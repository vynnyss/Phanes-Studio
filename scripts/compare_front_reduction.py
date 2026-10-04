"""Sequential, reproducible comparison on the user-approved bookshelf source."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

import psutil
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from studio_service import Studio, BLENDER

OUTPUT = ROOT / "outputs/remesh-comparison/front-20261004"
SOURCE = ROOT / "outputs/studio/d22cab3db100452a8d7de59d84debfc9/model.glb"
OUTPUT.mkdir(parents=True, exist_ok=True)
studio = Studio()
was_paused = studio.paused()
source_hash = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
comparison = {"source": str(SOURCE), "source_sha256": source_hash, "probes": [], "candidates": []}


def persist():
    (OUTPUT / "comparison.json").write_text(json.dumps(comparison, indent=2))


def run(method, target, mode="update", probe=False):
    name = f"{method}-{mode}-{target}" if method == "meshopt" else f"decimate-{target}"
    if probe:
        name += "-probe"
    folder = OUTPUT / name
    folder.mkdir(exist_ok=True)
    command = [
        str(BLENDER), "-b", "--factory-startup", "-t", "6",
        "--python", str(ROOT / "scripts/blender_asset_worker.py"), "--",
        "--source", str(SOURCE), "--output", str(folder),
        "--method", method, "--triangles", str(target), "--texture", "1024",
        "--meshopt-mode", mode,
    ]
    if probe:
        command.append("--remesh-only")
    samples = []
    with (folder / "worker.log").open("w") as log:
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
        started = time.monotonic()
        while process.poll() is None:
            time.sleep(.25)
            stage = "starting"
            progress = folder / "progress.json"
            try:
                stage = json.loads(progress.read_text())["stage"]
            except (OSError, ValueError):
                pass
            rss = 0
            try:
                parent = psutil.Process(process.pid)
                rss = sum(p.memory_info().rss for p in [parent] + parent.children(recursive=True))
            except psutil.Error:
                pass
            samples.append({"stage": stage, "rss_bytes": rss,
                            "system_available_bytes": psutil.virtual_memory().available})
            if time.monotonic() - started > 600:
                process.kill()
                raise RuntimeError("Comparison worker exceeded 10 minutes")
    report = json.loads((folder / "report.json").read_text())
    stages = {item["stage"] for item in samples}
    resources = {
        "peak_rss_by_stage": {
            stage: max(item["rss_bytes"] for item in samples if item["stage"] == stage)
            for stage in stages
        },
        "system_available_min_bytes": min((s["system_available_bytes"] for s in samples), default=None),
        "gpu_peak": None,
        "gpu_peak_reason": "Blender CPU bake and CPU/WASM simplification; VRAM peak not sampled",
    }
    (folder / "resources.json").write_text(json.dumps(resources, indent=2))
    entry = {"method": method, "mode": mode if method == "meshopt" else None,
             "target": target, "folder": str(folder), "result": report["result"],
             "actual": report.get("optimized", report.get("remeshed", {})).get("triangles"),
             "validation": report.get("geometry_validation"), "error": report.get("error")}
    print(json.dumps({key: entry[key] for key in ("method", "mode", "target", "result", "actual", "error")}), flush=True)
    return entry


try:
    requests.post("http://127.0.0.1:8080/api/queue/pause", timeout=15).raise_for_status()
    while any(job["status"] == "running" for job in studio.jobs()):
        time.sleep(2)
    for target in (12000, 8000, 6000, 4000):
        trials = []
        for mode in ("position", "update", "normal-update"):
            entry = run("meshopt", target, mode, probe=True)
            trials.append(entry)
            comparison["probes"].append(entry)
            persist()
        valid = [entry for entry in trials if entry["result"] == "remeshed" and entry["validation"]["passed"]]
        if valid:
            # Prefer meeting the budget, then the lowest worst-direction p95 distance.
            # This is a candidate choice for review, not a quality score or approval.
            def selection_key(entry):
                metrics = entry["validation"]["candidate"]
                distance = max(metrics[direction]["p95_relative"] for direction in ("source_to_candidate", "candidate_to_source"))
                return (entry["actual"] > target * 1.01, distance, entry["actual"])
            best = min(valid, key=selection_key)
            comparison["candidates"].append(run("meshopt", target, best["mode"]))
        if target != 12000:
            comparison["candidates"].append(run("simplify", target))
        persist()
    comparison["source_unchanged"] = hashlib.sha256(SOURCE.read_bytes()).hexdigest() == source_hash
    comparison["selection_rule"] = "Passed geometry checks; prefer target within 1%; then minimum worst-direction p95. Human review pending."
    persist()
finally:
    endpoint = "pause" if was_paused else "resume"
    requests.post("http://127.0.0.1:8080/api/queue/" + endpoint, timeout=15).raise_for_status()
    print("Queue previous state restored", flush=True)
