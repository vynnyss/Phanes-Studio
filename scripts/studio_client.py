"""Transport client used by both the desktop bootstrap and future agent tools."""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import subprocess
import threading
import time
import uuid
from urllib.parse import urlparse

import psutil
import requests

from studio_environment import PROJECT_ROOT, configure_environment, python_path


class StudioError(RuntimeError):
    pass


@contextmanager
def startup_lock(path, timeout=60):
    import msvcrt
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as stream:
        if path.stat().st_size == 0:
            stream.write(b"0")
            stream.flush()
        deadline = time.monotonic() + timeout
        while True:
            stream.seek(0)
            try:
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                break
            except OSError:
                if time.monotonic() >= deadline:
                    raise StudioError("Timed out waiting for Studio startup")
                time.sleep(0.1)
        try:
            yield
        finally:
            stream.seek(0)
            msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)


class StudioClient:
    def __init__(self, root=None):
        self.root = Path(root or os.environ.get("STUDIO_ROOT", PROJECT_ROOT)).resolve()
        self.data = self.root / "local_data/studio"
        self.manifest = self.data / "runtime.json"
        self.session = requests.Session()
        self.session.trust_env = False
        self.url = None
        self.instance_id = None

    def discover(self):
        try:
            recorded = json.loads(self.manifest.read_text(encoding="utf-8"))
            if Path(recorded["root"]).resolve() != self.root:
                return None
            parsed = urlparse(recorded["url"])
            if parsed.scheme != "http" or parsed.hostname != "127.0.0.1" or not parsed.port:
                return None
            owner = psutil.Process(recorded["pid"])
            if abs(owner.create_time() - recorded["process_created"]) > 0.01:
                return None
            response = self.session.get(recorded["url"] + "/api/runtime", timeout=(1, 2))
            response.raise_for_status()
            status = response.json()
            if (status.get("service") != "local-3d-studio" or status.get("protocol") != 1
                    or status.get("instance_id") != recorded["instance_id"]
                    or status.get("stopping") or Path(status["root"]).resolve() != self.root):
                return None
            self.url = recorded["url"]
            self.instance_id = recorded["instance_id"]
            return status
        except (OSError, ValueError, TypeError, KeyError, psutil.Error, requests.RequestException):
            return None

    def ensure(self, ui=False):
        status = self.discover()
        if status is None:
            configure_environment(self.root)
            with startup_lock(self.data / "startup.lock"):
                status = self.discover()
                if status is None:
                    executable = python_path(self.root)
                    if not executable.is_file():
                        raise StudioError(f"Studio Python not found: {executable}")
                    command = [
                        str(executable), "-u", str(Path(__file__).with_name("studio_runtime.py")),
                        "--root", str(self.root),
                    ]
                    idle = os.environ.get("STUDIO_IDLE_SECONDS")
                    if idle:
                        command.extend(["--idle-seconds", idle])
                    log_path = self.root / "logs/studio-runtime.log"
                    with log_path.open("ab") as log:
                        process = subprocess.Popen(
                            command, cwd=self.root, env=os.environ.copy(), stdin=subprocess.DEVNULL,
                            stdout=log, stderr=subprocess.STDOUT,
                            creationflags=subprocess.CREATE_NO_WINDOW,
                        )
                    deadline = time.monotonic() + 60
                    while time.monotonic() < deadline:
                        status = self.discover()
                        if status is not None:
                            break
                        if process.poll() is not None:
                            with log_path.open("rb") as log:
                                log.seek(max(0, log_path.stat().st_size - 2500))
                                detail = log.read().decode("utf-8", errors="replace")
                            raise StudioError(
                                "Studio could not start. An older executor may still be active. "
                                f"See {log_path}\n{detail}"
                            )
                        time.sleep(0.2)
                    else:
                        raise StudioError(f"Studio startup timed out. See {log_path}")
        if ui:
            self.request("POST", "/api/runtime/ui", timeout=(3, 120))
            status = self.request("GET", "/api/runtime")
        return status

    def request(self, method, path, timeout=(3, 60), **kwargs):
        if self.url is None:
            raise StudioError("Studio client is not connected")
        try:
            response = self.session.request(method, self.url + path, timeout=timeout, **kwargs)
        except requests.RequestException as error:
            raise StudioError(f"Studio request failed: {error}") from error
        if not response.ok:
            try:
                detail = response.json().get("detail", response.text)
            except ValueError:
                detail = response.text
            raise StudioError(f"HTTP {response.status_code}: {detail}")
        return response.json()

    def download(self, identifier, destination):
        destination = Path(destination).resolve()
        if destination.exists():
            raise StudioError("Destination already exists; choose a new filename")
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_name(destination.name + "." + uuid.uuid4().hex + ".part")
        try:
            with self.session.get(
                self.url + f"/api/models/{identifier}/glb", stream=True, timeout=(3, 60)
            ) as response:
                response.raise_for_status()
                with temporary.open("xb") as stream:
                    for chunk in response.iter_content(1024 * 1024):
                        stream.write(chunk)
            # Windows rename fails if another client created the destination meanwhile.
            temporary.rename(destination)
        except (OSError, requests.RequestException) as error:
            temporary.unlink(missing_ok=True)
            raise StudioError(f"Download failed: {error}") from error
        return {"model_id": identifier, "path": str(destination), "bytes": destination.stat().st_size}

    @contextmanager
    def keepalive(self):
        lease = self.request("POST", "/api/runtime/clients", json={"kind": "agent", "pid": os.getpid()})
        stop = threading.Event()
        session = requests.Session()
        session.trust_env = False
        route = self.url + "/api/runtime/clients/" + lease["client_id"]

        def renew():
            while not stop.wait(10):
                try:
                    response = session.put(route, timeout=(3, 5))
                    response.raise_for_status()
                except requests.RequestException:
                    return

        thread = threading.Thread(target=renew, daemon=True)
        thread.start()
        try:
            yield
        finally:
            stop.set()
            thread.join(timeout=10)
            session.close()
            try:
                self.request("DELETE", "/api/runtime/clients/" + lease["client_id"])
            except StudioError:
                pass

    def close(self):
        self.session.close()
