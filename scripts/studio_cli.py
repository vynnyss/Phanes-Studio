"""Stable JSON command interface for local AI agents and the desktop launcher."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

from studio_client import StudioClient, StudioError


class JsonParser(argparse.ArgumentParser):
    def error(self, message):
        print(json.dumps({"ok": False, "error": message}, ensure_ascii=False))
        raise SystemExit(2)


def build_parser():
    parser = JsonParser(description="3D Studio agent commands; results are JSON")
    parser.add_argument("--root", type=Path, help="Installation or isolated workspace root")
    commands = parser.add_subparsers(dest="command", required=True, parser_class=JsonParser)
    start = commands.add_parser("start")
    start.add_argument("--ui", action="store_true")
    commands.add_parser("status")
    for command in ("models", "history", "images", "jobs", "pause", "resume", "stop"):
        commands.add_parser(command)
    for command in ("job", "cancel"):
        subparser = commands.add_parser(command)
        subparser.add_argument("id")
    wait = commands.add_parser("wait")
    wait.add_argument("id")
    wait.add_argument("--timeout", type=float, default=7200)
    wait.add_argument("--poll", type=float, default=3)
    generate = commands.add_parser("generate")
    generate.add_argument("--image", type=Path, action="append", required=True)
    generate.add_argument("--resolution", type=int, choices=(512, 1024), default=1024)
    generate.add_argument("--seed", type=int, default=0)
    generate.add_argument("--faces", type=int, default=250000)
    generate.add_argument("--texture", type=int, choices=(512, 1024, 2048), default=2048)
    generate.add_argument("--request-key")
    generate.add_argument("--name")
    remesh = commands.add_parser("remesh")
    remesh.add_argument("--model", required=True)
    remesh.add_argument("--method", choices=("simplify", "meshopt", "instant", "quadriflow"),
                        default="simplify")
    remesh.add_argument("--triangles", type=int, default=12000)
    remesh.add_argument("--texture", type=int, choices=(512, 1024, 2048), default=2048)
    remesh.add_argument("--repair", action="store_true")
    remesh.add_argument("--request-key")
    export = commands.add_parser("export-lods")
    export.add_argument("--model", action="append", required=True)
    export.add_argument("--directory", type=Path, required=True)
    download = commands.add_parser("download")
    download.add_argument("--model", required=True)
    download.add_argument("--destination", type=Path, required=True)
    return parser


def execute(client, arguments):
    command = arguments.command
    if command in ("status", "stop"):
        status = client.discover()
        if status is None:
            return {"running": False}, 0
        if command == "status":
            return dict(status, running=True), 0
        return client.request("POST", "/api/runtime/stop"), 0
    status = client.ensure(ui=command == "start" and arguments.ui)
    if command == "start":
        return dict(status, running=True), 0
    if command in ("models", "history", "images", "jobs"):
        return client.request("GET", f"/api/{command}"), 0
    if command == "job":
        return client.request("GET", f"/api/jobs/{arguments.id}"), 0
    if command == "cancel":
        return client.request("POST", f"/api/jobs/{arguments.id}/cancel"), 0
    if command in ("pause", "resume"):
        return client.request("POST", f"/api/queue/{command}"), 0
    if command == "generate":
        if arguments.name and len(arguments.image) > 1:
            raise StudioError("--name accepts one image; omit it when submitting a batch")
        paths = [image.resolve() for image in arguments.image]
        for path in paths:
            if not path.is_file():
                raise StudioError(f"Image not found: {path}")
        jobs = []
        try:
            for path in paths:
                data = {"resolution": arguments.resolution, "seed": arguments.seed,
                        "faces": arguments.faces, "texture": arguments.texture}
                if arguments.name:
                    data["name"] = arguments.name
                if arguments.request_key:
                    key = arguments.request_key
                    if len(paths) > 1:
                        key += ":" + hashlib.sha256(path.read_bytes()).hexdigest()
                    data["request_key"] = key
                with path.open("rb") as image:
                    jobs.append(client.request(
                        "POST", "/api/jobs/generate", data=data,
                        files={"image": (path.name, image)},
                    ))
        except StudioError as error:
            return {"ok": False, "error": str(error), "submitted_jobs": jobs}, 1
        return {"jobs": jobs}, 0
    if command == "remesh":
        data = {"variant_id": arguments.model, "method": arguments.method,
                "triangles": arguments.triangles, "texture": arguments.texture,
                "repair": arguments.repair, "request_key": arguments.request_key}
        return client.request("POST", "/api/jobs/remesh", json=data), 0
    if command == "export-lods":
        return client.request("POST", "/api/exports/lods", json={
            "variant_ids": arguments.model,
            "target_directory": str(arguments.directory.resolve()),
        }), 0
    if command == "download":
        return client.download(arguments.model, arguments.destination), 0
    if command == "wait":
        if arguments.timeout <= 0 or arguments.poll <= 0:
            raise StudioError("--timeout and --poll must be positive")
        deadline = time.monotonic() + arguments.timeout
        with client.keepalive():
            while True:
                job = client.request("GET", f"/api/jobs/{arguments.id}")
                if job["status"] in ("completed", "failed", "cancelled", "interrupted"):
                    return job, 0 if job["status"] == "completed" else 2
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return {"ok": False, "error": "Wait timed out; job continues",
                            "job": job}, 3
                time.sleep(min(arguments.poll, remaining))
    raise StudioError("Unknown command")


def main():
    arguments = build_parser().parse_args()
    client = StudioClient(arguments.root)
    try:
        result, code = execute(client, arguments)
    except (StudioError, OSError, ValueError) as error:
        result, code = {"ok": False, "error": str(error)}, 1
    finally:
        client.close()
    print(json.dumps(result, ensure_ascii=False))
    return code


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
