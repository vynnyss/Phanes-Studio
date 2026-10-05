"""Integration checks in a disposable workspace; never submit work to the user's queue."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import uuid

import psutil

from studio_client import StudioClient, StudioError


PROJECT = Path(__file__).resolve().parents[1]
PYTHON = PROJECT / "runtime/official/code/venv/Scripts/python.exe"
CLI = PROJECT / "scripts/studio_cli.py"


def main():
    workspace = PROJECT / "local_data/desktop-validation" / uuid.uuid4().hex
    for directory in ("inputs", "outputs/baseline", "scripts", "logs"):
        (workspace / directory).mkdir(parents=True, exist_ok=True)
    image = workspace / "inputs/reference.png"
    shutil.copy2(PROJECT / "inputs/chair.png", image)
    shutil.copy2(PROJECT / "inputs/prop-bottle.webp", workspace / "inputs/second.webp")
    source = next((PROJECT / "outputs").glob("*/model.glb"))
    baseline = workspace / "outputs/baseline/model.glb"
    shutil.copy2(source, baseline)
    shutil.copy2(image, baseline.parent / "color0.png")
    (baseline.parent / "report.json").write_text(json.dumps({
        "result": "completed", "input": str(image), "triangles": 250000,
    }), encoding="utf-8")
    worker_source = '''import argparse, json, shutil, time
from pathlib import Path
parser = argparse.ArgumentParser()
parser.add_argument('--input')
parser.add_argument('--name')
parser.add_argument('--seed', type=int)
args, unused = parser.parse_known_args()
root = Path(__file__).resolve().parents[1]
output = root / 'outputs' / args.name
(output / 'progress.json').write_text(json.dumps({'stage': 'preprocess'}))
time.sleep(10)
(output / 'progress.json').write_text(json.dumps({'stage': 'export'}))
if args.seed == 1:
    (output / 'report.json').write_text(json.dumps({'result': 'failed', 'error': 'Controlled failure'}))
    raise SystemExit(1)
shutil.copy2(root / 'outputs/baseline/model.glb', output / 'model.glb')
shutil.copy2(args.input, output / 'color0.png')
(output / 'report.json').write_text(json.dumps({'result': 'completed', 'triangles': 12000}))
'''
    (workspace / "scripts/run_test.py").write_text(worker_source, encoding="utf-8")
    environment = dict(os.environ, STUDIO_ROOT=str(workspace), STUDIO_PYTHON=str(PYTHON),
                       STUDIO_IDLE_SECONDS="4", PYTHONUTF8="1", GRADIO_IS_E2E_TEST="1")
    os.environ["GRADIO_ANALYTICS_ENABLED"] = "False"
    checks = {}

    def command(*arguments, expected=0):
        result = subprocess.run(
            [str(PYTHON), str(CLI), "--root", str(workspace), *arguments],
            env=environment, capture_output=True, text=True, encoding="utf-8", timeout=90,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        assert result.returncode == expected, (arguments, result.stdout, result.stderr)
        return json.loads(result.stdout)

    def expect_error(call):
        try:
            call()
        except StudioError:
            return
        raise AssertionError("Expected operation to be rejected")

    client = StudioClient(workspace)
    processes = []
    try:
        assert command("status") == {"running": False}
        checks["status_does_not_start_service"] = True
        import_check = subprocess.run(
            [str(PYTHON), "-c", "import sys; sys.path.insert(0,sys.argv[1]); "
             "import studio_app,studio_api; "
             "assert 'gradio' not in sys.modules; "
             "from pathlib import Path; assert not (Path(sys.argv[2])/'local_data/studio/studio.db').exists()",
             str(PROJECT / "scripts"), str(workspace)],
            env=environment, capture_output=True, timeout=30,
        )
        assert import_check.returncode == 0, import_check.stderr
        checks["imports_have_no_executor_or_gradio_side_effects"] = True
        with ThreadPoolExecutor(max_workers=3) as pool:
            starts = list(pool.map(lambda _: command("start"), range(3)))
        assert len({status["instance_id"] for status in starts}) == 1
        assert all(not status["ui_ready"] for status in starts)
        processes.append(psutil.Process(starts[0]["pid"]))
        client.discover()
        checks["three_chats_share_one_headless_executor"] = True

        command("pause")
        models = command("models")
        assert len(models) == 1
        model_id = models[0]["id"]
        assert len(command("images")) == 2
        checks["legacy_history_and_references_imported"] = True

        def submit(_):
            return command("generate", "--image", str(image), "--resolution", "512",
                           "--request-key", "shared-idempotency")["jobs"][0]["job_id"]

        with ThreadPoolExecutor(max_workers=2) as pool:
            identifiers = list(pool.map(submit, range(2)))
        assert len(set(identifiers)) == 1
        first = identifiers[0]
        command("generate", "--image", str(image), "--seed", "7",
                "--request-key", "shared-idempotency", expected=1)
        command("remesh", "--model", model_id, "--triangles", "2", expected=1)
        remesh = command("remesh", "--model", model_id, "--method", "meshopt")["job_id"]
        command("cancel", remesh)
        assert command("job", remesh)["status"] == "cancelled"
        checks["idempotency_validation_remesh_and_pending_cancel"] = True

        package = command("export-lods", "--model", model_id,
                          "--directory", str(workspace / "exports"))
        assert Path(package["manifest"]).is_file()
        download = workspace / "download.glb"
        command("download", "--model", model_id, "--destination", str(download))
        assert hashlib.sha256(download.read_bytes()).digest() == hashlib.sha256(baseline.read_bytes()).digest()
        command("download", "--model", model_id, "--destination", str(download), expected=1)
        checks["lod_export_and_exact_download_without_overwrite"] = True

        # A paused pending queue can sleep; all records must survive the restart.
        command("stop")
        time.sleep(1)
        command("start")
        client.discover()
        assert command("job", first)["status"] == "pending"
        checks["paused_queue_survives_service_restart"] = True
        lease = client.request("POST", "/api/runtime/clients", json={"kind": "desktop"})
        time.sleep(5)
        assert client.discover() is not None
        expect_error(lambda: client.request("POST", "/api/runtime/stop"))
        client.request("DELETE", "/api/runtime/clients/" + lease["client_id"])
        checks["desktop_lease_prevents_idle_stop"] = True

        command("resume")
        deadline = time.monotonic() + 10
        while command("job", first)["status"] != "running":
            assert time.monotonic() < deadline
            time.sleep(0.2)
        expect_error(lambda: client.request("POST", "/api/runtime/stop"))
        time.sleep(5)
        assert client.discover() is not None
        assert command("wait", first, "--poll", "0.3", "--timeout", "30")["status"] == "completed"
        checks["active_worker_survives_window_and_chat_disconnection"] = True

        failed = command("generate", "--image", str(image), "--seed", "1")["jobs"][0]["job_id"]
        command("wait", failed, "--timeout", "0.1", "--poll", "0.1", expected=3)
        assert command("wait", failed, "--poll", "0.3", expected=2)["status"] == "failed"
        checks["failure_and_wait_timeout_are_machine_readable"] = True

        batch = command("generate", "--image", str(image), "--image", str(workspace / "inputs/second.webp"))
        for item in batch["jobs"]:
            command("wait", item["job_id"], "--poll", "0.3", "--timeout", "40")
        assert all(job["status"] != "running" for job in command("jobs"))
        checks["batch_runs_sequentially_on_one_executor"] = True

        # Mount the original UI onto an already-running headless service.
        mounted = command("start", "--ui")
        assert mounted["ui_ready"]
        client.discover()
        response = client.session.get(client.url + "/config", timeout=15)
        response.raise_for_status()
        components = response.json()["components"]
        assert any(item["type"] == "model3d" for item in components)
        assert sum(item["type"] == "gallery" for item in components) == 3
        assert any(item["type"] == "gallery" and item["props"].get("elem_id") == "texture-viewer"
                   for item in components)
        checks["lazy_gradio_mount_preserves_existing_components"] = True

        import gradio_client
        ui_client = gradio_client.Client(client.url, verbose=False, httpx_kwargs={"trust_env": False})
        configuration = response.json()
        callback_id = next(
            item["id"] for item in configuration["dependencies"]
            if item.get("api_name") == "models_next_page"
        )
        selection = ui_client.predict(fn_index=callback_id)
        assert selection is not None
        ui_client.close()
        checks["live_gradio_callback_queue_started_after_lazy_mount"] = True
        status = client.discover()
        owner = psutil.Process(status["pid"])
        time.sleep(6)
        assert not owner.is_running(), "Idle Studio should exit and close its listener"
        assert command("status") == {"running": False}
        checks["idle_exit_closes_port_and_removes_manifest"] = True
        restarted = command("start")
        assert restarted["instance_id"] != mounted["instance_id"]
        assert len(command("models")) == 4
        checks["completed_history_survives_idle_restart"] = True
        command("stop")
        report = {"ok": True, "workspace": str(workspace), "checks": checks,
                  "worker": "controlled fixture; existing GLB copied; no GPU inference"}
        destination = PROJECT / "local_data/studio/desktop-runtime-validation.json"
        destination.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False))
    finally:
        if client.discover() is not None:
            try:
                client.request("POST", "/api/queue/pause")
                client.request("POST", "/api/runtime/stop")
            except StudioError:
                pass
        client.close()


if __name__ == "__main__":
    main()
