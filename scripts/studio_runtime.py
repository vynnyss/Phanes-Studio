"""One on-demand executor shared by desktop windows and agent clients."""
import argparse
import asyncio
from contextlib import AsyncExitStack, asynccontextmanager
import json
import os
from pathlib import Path
import socket
import threading
import time
import uuid

from studio_environment import configure_environment


SERVICE_NAME = "local-3d-studio"
PROTOCOL_VERSION = 1


class ActivityMiddleware:
    def __init__(self, app, runtime):
        self.app = app
        self.runtime = runtime

    async def __call__(self, scope, receive, send):
        if scope["type"] not in ("http", "websocket"):
            return await self.app(scope, receive, send)
        with self.runtime.guard:
            if self.runtime.stopping:
                rejected = True
            else:
                rejected = False
                self.runtime.requests += 1
                self.runtime.last_activity = time.monotonic()
        if rejected:
            if scope["type"] == "websocket":
                await send({"type": "websocket.close", "code": 1013})
            else:
                body = b'{"detail":"Studio is shutting down; retry the command"}'
                await send({"type": "http.response.start", "status": 503,
                            "headers": [(b"content-type", b"application/json")]})
                await send({"type": "http.response.body", "body": body})
            return
        try:
            await self.app(scope, receive, send)
        finally:
            with self.runtime.guard:
                self.runtime.requests -= 1
                self.runtime.last_activity = time.monotonic()


class ManagedRuntime:
    def __init__(self, studio, root, port, idle_seconds):
        import psutil
        self.studio = studio
        self.root = root
        self.port = port
        self.idle_seconds = idle_seconds
        self.instance_id = uuid.uuid4().hex
        self.created = psutil.Process().create_time()
        self.manifest = root / "local_data/studio/runtime.json"
        self.guard = threading.RLock()
        self.last_activity = time.monotonic()
        self.requests = 0
        self.clients = {}
        self.stopping = False
        self.ui_ready = False
        self.ui_lock = asyncio.Lock()
        self.resources = AsyncExitStack()
        self.server = None
        self.api = None

    def identity(self):
        return {
            "service": SERVICE_NAME,
            "protocol": PROTOCOL_VERSION,
            "instance_id": self.instance_id,
            "root": str(self.root),
            "pid": os.getpid(),
            "process_created": self.created,
            "url": f"http://127.0.0.1:{self.port}",
        }

    def expire_clients(self):
        import psutil
        now = time.monotonic()
        for identifier, client in list(self.clients.items()):
            expired = client["expires"] <= now
            if client.get("pid"):
                try:
                    owner = psutil.Process(client["pid"])
                    expired = expired or abs(owner.create_time() - client["process_created"]) > 0.01
                except psutil.Error:
                    expired = True
            if expired:
                self.clients.pop(identifier, None)

    def status(self):
        with self.guard:
            self.expire_clients()
            clients = [
                {"id": identifier, "kind": value["kind"], "pid": value.get("pid")}
                for identifier, value in self.clients.items()
            ]
            return dict(self.identity(), ui_ready=self.ui_ready, clients=clients,
                        work=self.studio.work_state(), stopping=self.stopping,
                        idle_seconds=self.idle_seconds)

    def register_client(self, kind, pid=None):
        import psutil
        created = None
        if pid is not None:
            try:
                created = psutil.Process(pid).create_time()
            except psutil.Error as error:
                raise ValueError("Client process is unavailable") from error
        identifier = uuid.uuid4().hex
        with self.guard:
            self.clients[identifier] = {
                "kind": kind, "pid": pid, "process_created": created,
                "expires": time.monotonic() + 45,
            }
        return {"client_id": identifier, "ttl_seconds": 45}

    async def enable_ui(self):
        async with self.ui_lock:
            if self.ui_ready:
                return self.identity()

            def construct():
                import gradio as gr
                from fastapi import FastAPI
                from studio_ui import build_demo
                from studio_pagination import PAGINATION_CSS
                demo = build_demo(self.studio)
                container = gr.mount_gradio_app(
                    FastAPI(), demo, path="/", css=PAGINATION_CSS,
                    server_name="127.0.0.1", server_port=self.port,
                    ssr_mode=False, mcp_server=False,
                    allowed_paths=[
                        str(self.root / "outputs"), str(self.root / "inputs"),
                        str(self.root / "local_data/studio/images"),
                    ],
                )
                return container

            container = await asyncio.to_thread(construct)
            await self.resources.enter_async_context(container.router.lifespan_context(container))
            self.api.mount("/", container)
            self.ui_ready = True
            return self.identity()

    def can_stop(self, current_request=False):
        self.expire_clients()
        work = self.studio.work_state()
        executing = work["running"] or (work["pending"] and not work["paused"])
        allowed_requests = 1 if current_request else 0
        return not executing and not self.clients and self.requests <= allowed_requests

    async def monitor(self):
        while True:
            await asyncio.sleep(1)
            with self.guard:
                elapsed = time.monotonic() - self.last_activity
                if elapsed >= self.idle_seconds and self.can_stop():
                    self.stopping = True
                    self.server.should_exit = True
                    return

    @asynccontextmanager
    async def lifespan(self, app):
        self.studio.start()
        monitor = None
        try:
            temporary = self.manifest.with_suffix(".tmp")
            temporary.write_text(json.dumps(self.identity(), indent=2), encoding="utf-8")
            os.replace(temporary, self.manifest)
            monitor = asyncio.create_task(self.monitor())
            yield
        finally:
            if monitor:
                monitor.cancel()
                try:
                    await monitor
                except asyncio.CancelledError:
                    pass
            await self.resources.aclose()
            self.studio.close()
            if self.manifest.is_file():
                recorded = json.loads(self.manifest.read_text(encoding="utf-8"))
                if recorded.get("instance_id") == self.instance_id:
                    self.manifest.unlink(missing_ok=True)

    def build_api(self):
        from fastapi import HTTPException
        from pydantic import BaseModel, Field
        from studio_api import create_api

        api = create_api(self.studio, lifespan=self.lifespan)
        self.api = api
        api.add_middleware(ActivityMiddleware, runtime=self)

        @api.get("/api/runtime")
        def status():
            return self.status()

        @api.post("/api/runtime/ui")
        async def enable_ui():
            return await self.enable_ui()

        class ClientRequest(BaseModel):
            kind: str = Field(default="agent", pattern="^(desktop|agent)$")
            pid: int | None = Field(default=None, gt=0)

        @api.post("/api/runtime/clients")
        def register_client(request: ClientRequest):
            try:
                return self.register_client(request.kind, request.pid)
            except ValueError as error:
                raise HTTPException(status_code=400, detail=str(error)) from error

        @api.put("/api/runtime/clients/{identifier}")
        def heartbeat(identifier: str):
            with self.guard:
                self.expire_clients()
                client = self.clients.get(identifier)
                if client is None:
                    raise HTTPException(status_code=404, detail="Client lease expired")
                client["expires"] = time.monotonic() + 45
            return {"ttl_seconds": 45}

        @api.delete("/api/runtime/clients/{identifier}")
        def release_client(identifier: str):
            with self.guard:
                self.clients.pop(identifier, None)
            return {"released": True}

        @api.post("/api/runtime/stop")
        def stop():
            with self.guard:
                if not self.can_stop(current_request=True):
                    raise HTTPException(status_code=409, detail="Studio has clients or active work")
                self.stopping = True
                self.server.should_exit = True
            return {"stopping": True}

        return api


def main():
    parser = argparse.ArgumentParser(description="Managed local Studio service")
    parser.add_argument("--root", type=Path)
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--idle-seconds", type=float, default=120)
    arguments = parser.parse_args()
    if arguments.idle_seconds < 1:
        parser.error("--idle-seconds must be at least 1")
    root = configure_environment(arguments.root)

    import uvicorn
    from studio_service import Studio

    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", arguments.port))
    listener.listen(128)
    listener.setblocking(False)
    runtime = ManagedRuntime(Studio(), root, listener.getsockname()[1], arguments.idle_seconds)
    configuration = uvicorn.Config(
        runtime.build_api(), host="127.0.0.1", port=runtime.port,
        log_level="info", access_log=False, timeout_graceful_shutdown=30,
    )
    runtime.server = uvicorn.Server(configuration)
    try:
        runtime.server.run(sockets=[listener])
    finally:
        listener.close()


if __name__ == "__main__":
    main()
