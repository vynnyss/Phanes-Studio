"""Persistent local job queue shared by UI and agent clients."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import threading
import time
import uuid

import psutil
from PIL import Image

from studio_progress import read_progress

ROOT = Path(os.environ.get("STUDIO_ROOT", Path(__file__).resolve().parents[1])).resolve()
CODE = ROOT / "runtime/official/code"
PYTHON = Path(os.environ.get("STUDIO_PYTHON", CODE / "venv/Scripts/python.exe"))
BLENDER = Path(os.environ.get(
    "ASSET_BLENDER", "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"
))
INSTANT = ROOT / "runtime/tools/instant-meshes/bin/Instant Meshes.exe"
DATA = ROOT / "local_data/studio"
DB = DATA / "studio.db"


def now():
    return time.time()


def connect():
    connection = sqlite3.connect(DB, timeout=30)
    connection.row_factory = sqlite3.Row
    return connection


def decode(row):
    result = dict(row)
    if "parameters" in result:
        result["parameters"] = json.loads(result["parameters"])
    return result


class Studio:
    def __init__(self):
        DATA.mkdir(parents=True, exist_ok=True)
        self.stop = threading.Event()
        self.thread = None
        self.process = None
        self.guard = threading.Lock()
        self.started = False
        with connect() as db:
            db.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS variants (
                    id TEXT PRIMARY KEY,
                    asset_id TEXT NOT NULL,
                    parent_id TEXT,
                    name TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    model TEXT NOT NULL,
                    thumbnail TEXT,
                    reference TEXT,
                    report TEXT,
                    created REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    kind TEXT NOT NULL,
                    parent_id TEXT,
                    name TEXT NOT NULL,
                    input TEXT NOT NULL,
                    parameters TEXT NOT NULL,
                    status TEXT NOT NULL,
                    stage TEXT NOT NULL,
                    output TEXT NOT NULL,
                    error TEXT,
                    origin TEXT NOT NULL,
                    request_key TEXT UNIQUE,
                    created REAL NOT NULL,
                    finished REAL
                );
                CREATE TABLE IF NOT EXISTS reference_images (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    path TEXT NOT NULL,
                    created REAL NOT NULL,
                    last_used REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS variant_reviews (
                    variant_id TEXT PRIMARY KEY,
                    state TEXT NOT NULL,
                    reason TEXT,
                    created REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY, value TEXT NOT NULL
                );
                INSERT OR IGNORE INTO settings VALUES ('paused', '0');
            """)

        with connect() as db:
            columns = {row["name"] for row in db.execute("PRAGMA table_info(jobs)")}
            if "started" not in columns:
                db.execute("ALTER TABLE jobs ADD COLUMN started REAL")
                db.execute(
                    "UPDATE jobs SET started=created WHERE status IN "
                    "('running','completed','failed','interrupted')"
                )

    def start(self):
        if self.started:
            return
        # One Studio instance owns all subprocesses; duplicate servers cannot share a worker.
        import msvcrt
        self.lock_file = (DATA / "executor.lock").open("a+b")
        self.lock_file.seek(0)
        self.lock_file.write(b"0")
        self.lock_file.flush()
        self.lock_file.seek(0)
        try:
            msvcrt.locking(self.lock_file.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError as error:
            self.lock_file.close()
            raise RuntimeError("Another Studio executor is already active") from error
        with connect() as db:
            db.execute(
                "UPDATE jobs SET status='interrupted',stage='interrupted',"
                "error='Service stopped during execution; original preserved',finished=? "
                "WHERE status='running'", (now(),)
            )
        self.import_existing()
        self.import_reference_images()
        self.thread = threading.Thread(target=self.loop, daemon=True)
        self.started = True
        self.thread.start()

    def close(self):
        if not self.started:
            return
        self.stop.set()
        if self.process and self.process.poll() is None:
            self.terminate_tree()
        if self.thread:
            self.thread.join(timeout=15)
        if hasattr(self, "lock_file"):
            self.lock_file.close()
        self.started = False

    def work_state(self):
        """Count all live work, including jobs outside the recent-jobs page."""
        with connect() as db:
            counts = dict(db.execute(
                "SELECT status,COUNT(*) FROM jobs "
                "WHERE status IN ('pending','running') GROUP BY status"
            ).fetchall())
            paused = db.execute("SELECT value FROM settings WHERE key='paused'").fetchone()[0]
        return {
            "running": counts.get("running", 0),
            "pending": counts.get("pending", 0),
            "paused": paused == "1",
        }

    def import_existing(self):
        for folder in (ROOT / "outputs").iterdir():
            if not folder.is_dir() or folder.name in ("remesh-tests", "studio"):
                continue
            model = folder / "model.glb"
            report = folder / "report.json"
            if not model.is_file() or not report.is_file():
                continue
            try:
                metadata = json.loads(report.read_text(encoding="utf-8-sig"))
            except (ValueError, OSError):
                continue
            if metadata.get("result") != "completed":
                continue
            identifier = "legacy-" + uuid.uuid5(uuid.NAMESPACE_URL, str(model)).hex
            thumbnail = folder / "blender/blender-render.png"
            if not thumbnail.is_file():
                candidates = list(folder.glob("*color*0.png"))
                thumbnail = candidates[0] if candidates else Path(metadata.get("input", ""))
            self.add_variant(
                identifier, identifier, None, folder.name, "high",
                model, thumbnail, metadata.get("input"), report,
            )
        test_root = ROOT / "outputs/remesh-tests"
        if test_root.is_dir():
            for report in test_root.glob("*/report.json"):
                try:
                    metadata = json.loads(report.read_text(encoding="utf-8-sig"))
                except (ValueError, OSError):
                    continue
                if metadata.get("result") != "completed":
                    continue
                model = report.parent / "model.glb"
                if not model.is_file():
                    continue
                parent = self.find_model(metadata["source"])
                if parent:
                    identifier = "test-" + uuid.uuid5(uuid.NAMESPACE_URL, str(model)).hex
                    self.add_variant(
                        identifier, parent["asset_id"], parent["id"], report.parent.name,
                        "low", model, report.parent / "optimized-0.png",
                        parent["reference"], report,
                    )

    def remember_image(self, path, name=None, used_at=None):
        source = Path(path)
        content = source.read_bytes()
        identifier = hashlib.sha256(content).hexdigest()
        with Image.open(source) as image:
            image.verify()
            image_format = image.format
        suffixes = {"PNG": ".png", "JPEG": ".jpg", "WEBP": ".webp"}
        suffix = suffixes.get(image_format, source.suffix.lower())
        directory = DATA / "images"
        directory.mkdir(parents=True, exist_ok=True)
        retained = directory / (identifier + suffix)
        if not retained.is_file():
            # Keep a permanent copy independent of upload/session/job caches.
            retained.write_bytes(content)
        timestamp = now() if used_at is None else used_at
        with connect() as db:
            db.execute(
                "INSERT INTO reference_images VALUES (?,?,?,?,?) "
                "ON CONFLICT(id) DO UPDATE SET last_used=MAX(last_used,excluded.last_used)",
                (identifier, (name or source.stem)[:120], str(retained), timestamp, timestamp),
            )
        return identifier

    def import_reference_images(self):
        for path in sorted((ROOT / "inputs").iterdir()):
            if path.is_file() and path.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
                self.remember_image(path, used_at=path.stat().st_mtime)
        with connect() as db:
            jobs = db.execute(
                "SELECT input,name,created FROM jobs WHERE kind='generate' ORDER BY created"
            ).fetchall()
            models = db.execute(
                "SELECT reference,name,created FROM variants WHERE kind='high' AND reference IS NOT NULL"
            ).fetchall()
        for row in models:
            path = Path(row["reference"])
            if path.is_file():
                self.remember_image(path, name=row["name"], used_at=path.stat().st_mtime)
        for row in jobs:
            path = Path(row["input"])
            if path.is_file():
                self.remember_image(path, name=row["name"], used_at=row["created"])

    def reference_images(self):
        with connect() as db:
            rows = db.execute(
                "SELECT * FROM reference_images ORDER BY last_used DESC,id"
            ).fetchall()
        return [dict(row) for row in rows if Path(row["path"]).is_file()]

    def reference_image(self, identifier):
        with connect() as db:
            row = db.execute(
                "SELECT * FROM reference_images WHERE id=?", (identifier,)
            ).fetchone()
        if row is None:
            raise ValueError("Reference image not found")
        path = Path(row["path"]).resolve()
        if not path.is_relative_to((DATA / "images").resolve()) or not path.is_file():
            raise ValueError("Reference image unavailable")
        return dict(row)

    def add_variant(self, identifier, asset_id, parent_id, name, kind,
                    model, thumbnail, reference, report):
        with connect() as db:
            db.execute(
                "INSERT OR IGNORE INTO variants VALUES (?,?,?,?,?,?,?,?,?,?)",
                (identifier, asset_id, parent_id, name, kind, str(model),
                 str(thumbnail) if thumbnail else None,
                 str(reference) if reference else None,
                 str(report) if report else None, now()),
            )

    def variants(self):
        with connect() as db:
            rows = db.execute("SELECT v.*,COALESCE(q.state,'unreviewed') AS quality_status,q.reason AS quality_reason "
                "FROM variants v LEFT JOIN variant_reviews q ON q.variant_id=v.id ORDER BY v.created DESC,v.id").fetchall()
        return [decode(row) for row in rows]

    def history_entries(self):
        models = self.variants()
        with connect() as db:
            jobs = [decode(row) for row in db.execute(
                "SELECT * FROM jobs WHERE started IS NOT NULL ORDER BY started DESC,id"
            )]
        by_id = {job["id"]: job for job in jobs}
        identifiers = {model["id"] for model in models}
        entries = []
        for model in models:
            job = by_id.get(model["id"])
            entries.append(dict(model, status="completed", stage="completed",
                                started=job["started"] if job else model["created"]))
        for job in jobs:
            if job["id"] in identifiers:
                continue
            parent = self.variant(job["parent_id"]) if job["parent_id"] else None
            entries.append({
                "id": job["id"], "name": job["name"], "kind": "low" if parent else "high",
                "asset_id": parent["asset_id"] if parent else job["id"],
                "parent_id": job["parent_id"], "model": None,
                "reference": parent["reference"] if parent else job["input"],
                "thumbnail": parent["thumbnail"] if parent else job["input"],
                "report": str(Path(job["output"]) / "report.json"),
                "created": job["created"], "started": job["started"],
                "status": job["status"], "stage": job["stage"], "error": job["error"],
                "output": job["output"],
            })
        return sorted(entries, key=lambda entry: (entry["started"],entry["id"]), reverse=True)

    def history_entry(self, identifier):
        for entry in self.history_entries():
            if entry["id"] == identifier:
                return entry
        raise ValueError("History item not found")

    def running_references(self):
        with connect() as db:
            jobs = [decode(row) for row in db.execute(
                "SELECT * FROM jobs WHERE status='running' AND kind='generate'"
            )]
        return {
            hashlib.sha256(Path(job["input"]).read_bytes()).hexdigest(): job
            for job in jobs if Path(job["input"]).is_file()
        }

    def find_model(self, path):
        with connect() as db:
            row = db.execute("SELECT * FROM variants WHERE model=?", (str(path),)).fetchone()
        return decode(row) if row else None

    def variant(self, identifier):
        with connect() as db:
            row = db.execute("SELECT v.*,COALESCE(q.state,'unreviewed') AS quality_status,q.reason AS quality_reason "
                "FROM variants v LEFT JOIN variant_reviews q ON q.variant_id=v.id WHERE v.id=?", (identifier,)).fetchone()
        if row is None:
            raise ValueError("Model not found")
        result = decode(row)
        path = Path(result["model"]).resolve()
        if not path.is_relative_to((ROOT / "outputs").resolve()) or not path.is_file():
            raise ValueError("Model artifact unavailable")
        return result

    def jobs(self):
        with connect() as db:
            rows = db.execute("SELECT * FROM jobs ORDER BY created DESC LIMIT 200").fetchall()
        return [decode(row) for row in rows]

    def job(self, identifier):
        with connect() as db:
            row = db.execute("SELECT * FROM jobs WHERE id=?", (identifier,)).fetchone()
        if not row:
            raise ValueError("Job not found")
        return decode(row)

    def queue_jobs(self):
        with connect() as db:
            rows = db.execute(
                "SELECT * FROM jobs WHERE status IN ('pending','running') "
                "ORDER BY CASE WHEN status='running' THEN 0 ELSE 1 END,created,id"
            ).fetchall()
        return [decode(row) for row in rows]

    def finished_jobs(self):
        with connect() as db:
            rows = db.execute(
                "SELECT * FROM jobs WHERE status IN "
                "('completed','cancelled','failed','interrupted') "
                "ORDER BY COALESCE(finished,created) DESC,id LIMIT 200"
            ).fetchall()
        return [decode(row) for row in rows]

    def paused(self):
        with connect() as db:
            return db.execute("SELECT value FROM settings WHERE key='paused'").fetchone()[0] == "1"

    def pause(self, value):
        with connect() as db:
            db.execute("UPDATE settings SET value=? WHERE key='paused'", ("1" if value else "0",))

    def enqueue(self, kind, name, input_path, parameters, parent_id=None,
                origin="ui", request_key=None):
        with self.guard:
            return self._enqueue(kind, name, input_path, parameters, parent_id, origin, request_key)

    def _enqueue(self, kind, name, input_path, parameters, parent_id=None,
                 origin="ui", request_key=None):
        if request_key:
            with connect() as db:
                old = db.execute("SELECT * FROM jobs WHERE request_key=?", (request_key,)).fetchone()
            if old:
                previous = decode(old)
                if previous["kind"] != kind or previous["parameters"] != parameters:
                    raise ValueError("Request key already used with different parameters")
                if kind == "remesh" and previous["parent_id"] != parent_id:
                    raise ValueError("Request key already used for another model")
                if kind == "generate":
                    old_hash = hashlib.sha256(Path(previous["input"]).read_bytes()).hexdigest()
                    new_hash = hashlib.sha256(Path(input_path).read_bytes()).hexdigest()
                    if old_hash != new_hash:
                        raise ValueError("Request key already used for another image")
                return previous["id"]
        identifier = uuid.uuid4().hex
        output = ROOT / "outputs/studio" / identifier
        output.mkdir(parents=True)
        source = Path(input_path)
        if kind == "generate":
            if source.stat().st_size > 32 * 1024 * 1024:
                raise ValueError("Image exceeds 32 MB")
            with Image.open(source) as image:
                image.verify()
            retained = output / ("source" + source.suffix.lower())
            shutil.copy2(source, retained)
            source = retained
        with connect() as db:
            db.execute(
                "INSERT INTO jobs (id,kind,parent_id,name,input,parameters,status,stage,output,error,"
                "origin,request_key,created,finished) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (identifier, kind, parent_id, name[:120], str(source), json.dumps(parameters),
                 "pending", "pending", str(output), None, origin[:32], request_key, now(), None),
            )
        if kind == "generate":
            self.remember_image(source, name=name)
        return identifier

    def enqueue_generate(self, path, resolution=1024, seed=0, faces=250000,
                         texture=2048, origin="ui", request_key=None, name=None):
        if resolution not in (512, 1024) or texture not in (512, 1024, 2048):
            raise ValueError("Unsupported resolution or texture size")
        if not 1000 <= faces <= 1000000 or not 0 <= seed < 2**31:
            raise ValueError("Invalid face budget or seed")
        if name is None:
            digest = hashlib.sha256(Path(path).read_bytes()).hexdigest()
            with connect() as db:
                known = db.execute(
                    "SELECT name FROM reference_images WHERE id=?", (digest,)
                ).fetchone()
            name = known["name"] if known else Path(path).stem
        return self.enqueue(
            "generate", name, path,
            {"resolution": resolution, "seed": seed, "faces": faces, "texture": texture},
            origin=origin, request_key=request_key,
        )

    def enqueue_remesh(self, variant_id, method, triangles=12000, texture=2048,
                       repair=False, origin="ui", request_key=None):
        parent = self.variant(variant_id)
        if parent["quality_status"] == "rejected":
            raise ValueError("Esta versão foi rejeitada; selecione o high original para otimizar")
        if method not in ("instant", "quadriflow", "simplify", "meshopt"):
            raise ValueError("Unknown remesh method")
        if not 500 <= triangles <= 200000 or texture not in (512, 1024, 2048):
            raise ValueError("Invalid budget or texture size")
        return self.enqueue(
            "remesh", parent["name"] + " · " + method, parent["model"],
            {"method": method, "triangles": triangles, "texture": texture, "repair": bool(repair)},
            parent_id=parent["id"], origin=origin, request_key=request_key,
        )

    def cancel(self, identifier):
        with connect() as db:
            changed = db.execute(
                "UPDATE jobs SET status='cancelled',stage='cancelled',finished=? "
                "WHERE id=? AND status='pending'", (now(), identifier)
            ).rowcount
        if not changed:
            raise ValueError("Only pending jobs can be cancelled")

    def terminate_tree(self):
        try:
            parent = psutil.Process(self.process.pid)
            children = parent.children(recursive=True)
            for process in children:
                process.terminate()
            parent.terminate()
            psutil.wait_procs(children + [parent], timeout=10)
            for process in children + [parent]:
                if process.is_running():
                    process.kill()
        except psutil.Error:
            pass

    def command(self, job):
        params = job["parameters"]
        if job["kind"] == "generate":
            return [
                str(PYTHON), "-u", str(ROOT / "scripts/run_test.py"),
                "--input", job["input"], "--resolution", str(params["resolution"]),
                "--name", "studio/" + job["id"], "--seed", str(params["seed"]),
                "--faces", str(params["faces"]), "--texture", str(params["texture"]),
            ]
        command = [
            str(BLENDER), "-b", "--factory-startup", "-t", "6",
            "--python", str(ROOT / "scripts/blender_asset_worker.py"), "--",
            "--source", job["input"], "--output", job["output"],
            "--method", params["method"], "--instant", str(INSTANT),
            "--triangles", str(params["triangles"]), "--texture", str(params["texture"]),
        ]
        if params["repair"]:
            command.append("--voxel-repair")
        return command

    def loop(self):
        while not self.stop.wait(1):
            if self.paused():
                continue
            with connect() as db:
                row = db.execute(
                    "SELECT * FROM jobs WHERE status='pending' ORDER BY created,id LIMIT 1"
                ).fetchone()
                if row is None:
                    continue
                job = decode(row)
                db.execute("UPDATE jobs SET status='running',stage='starting',started=? WHERE id=?",
                           (now(), job["id"]))
            self.execute(job)

    def execute(self, job):
        directory = Path(job["output"])
        samples = []
        try:
            env = os.environ.copy()
            env["PYTHONUTF8"] = "1"
            env["SPARSE_DEBUG"] = "0"
            with (directory / "worker.log").open("w", encoding="utf-8") as log:
                self.process = subprocess.Popen(
                    self.command(job), cwd=ROOT, env=env,
                    stdout=log, stderr=subprocess.STDOUT,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
                started = time.monotonic()
                while self.process.poll() is None:
                    if self.stop.wait(1):
                        self.terminate_tree()
                        raise RuntimeError("Service stopped during job")
                    if time.monotonic() - started > 7200:
                        self.terminate_tree()
                        raise RuntimeError("Job exceeded two-hour timeout")
                    rss = 0
                    private = 0
                    try:
                        parent = psutil.Process(self.process.pid)
                        for process in [parent] + parent.children(recursive=True):
                            info = process.memory_info()
                            rss += info.rss
                            private += getattr(info, "private", 0)
                    except psutil.Error:
                        pass
                    samples.append({"time_s": time.monotonic() - started, "rss_bytes": rss,
                                    "private_bytes": private, "system_available": psutil.virtual_memory().available})
                    stage = read_progress(directory, "starting")["stage"]
                    with connect() as db:
                        db.execute("UPDATE jobs SET stage=? WHERE id=?", (stage, job["id"]))
            report_path = directory / "report.json"
            report = json.loads(report_path.read_text(encoding="utf-8-sig")) if report_path.is_file() else {}
            if self.process.returncode != 0 or report.get("result") != "completed":
                raise RuntimeError(report.get("error", f"Worker exited {self.process.returncode}; see worker.log"))
            model = directory / "model.glb"
            if not model.is_file() or model.stat().st_size < 20:
                raise RuntimeError("Worker did not produce a valid GLB artifact")
            with model.open("rb") as stream:
                header = stream.read(12)
            if header[:4] != b"glTF" or int.from_bytes(header[8:12], "little") != model.stat().st_size:
                raise RuntimeError("Invalid GLB header or length")
            if job["kind"] == "remesh":
                parent = self.variant(job["parent_id"])
                thumbnail = directory / "optimized-0.png"
                asset_id = parent["asset_id"]
                reference = parent["reference"]
            else:
                thumbnails = list(directory.glob("*color*0.png"))
                thumbnail = thumbnails[0] if thumbnails else Path(job["input"])
                asset_id = job["id"]
                reference = job["input"]
            self.add_variant(job["id"], asset_id, job["parent_id"], job["name"],
                             "low" if job["kind"] == "remesh" else "high",
                             model, thumbnail, reference, report_path)
            with connect() as db:
                db.execute("UPDATE jobs SET status='completed',stage='completed',finished=? WHERE id=?",
                           (now(), job["id"]))
        except Exception as error:
            with connect() as db:
                status = "interrupted" if self.stop.is_set() else "failed"
                db.execute("UPDATE jobs SET status=?,stage=?,error=?,finished=? WHERE id=?",
                           (status, status, str(error), now(), job["id"]))
        finally:
            (directory / "job-resources.json").write_text(json.dumps({
                "peak_tree_rss_bytes": max((sample["rss_bytes"] for sample in samples), default=None),
                "peak_tree_private_bytes": max((sample["private_bytes"] for sample in samples), default=None),
                "samples": samples,
                "gpu_peak": None,
                "gpu_peak_reason": "Studio monitor samples process/system RAM; generation worker has separate GPU log",
            }, indent=2), encoding="utf-8")
            self.process = None
