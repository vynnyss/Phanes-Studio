"""Sequential UVgami/OptCuts worker, launched exclusively by the Studio queue."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time

import numpy as np

from uvgami_transfer import transfer_uv


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--blender", required=True)
    parser.add_argument("--engine", type=Path, required=True)
    parser.add_argument("--texture", type=int, choices=(512, 1024, 2048), default=1024)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    report_path = args.output / "report.json"
    started = time.perf_counter()
    protected = [args.source, args.source.with_name("model.glb")]
    hashes = {
        str(path): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in protected
    }
    script = Path(__file__).with_name("blender_uvgami_worker.py")
    blender_command = [
        args.blender, "-b", "--factory-startup", "-t", "6",
        "--python-exit-code", "1", "--python", str(script), "--",
        "--source", str(args.source),
        "--output", str(args.output),
        "--texture", str(args.texture),
    ]
    report = {"result": "failed", "method": "uvgami-optcuts", "source": str(args.source)}
    try:
        subprocess.run(blender_command + ["--phase", "prepare"], check=True)
        (args.output / "progress.json").write_text(json.dumps({"stage": "uvgami"}), encoding="utf-8")
        engine_output = args.output / "optcuts"
        engine_output.mkdir()
        # OptCuts concatenates its output directory and filename; the separator is required.
        command = [
            str(args.engine),
            "-i", str(args.output / "low.obj"),
            "-o", engine_output.as_posix() + "/",
            "-u", "4.2", "-s", "100", "-t", "6",
        ]
        engine_started = time.perf_counter()
        with (args.output / "engine.log").open("w", encoding="utf-8") as log:
            subprocess.run(
                command, stdout=log, stderr=subprocess.STDOUT,
                check=True, timeout=6600,
            )
        engine = {
            "version": "1.21.9",
            "priority": "BALANCED",
            "command": command,
            "elapsed_s": time.perf_counter() - engine_started,
        }
        (args.output / "engine.json").write_text(json.dumps(engine, indent=2), encoding="utf-8")
        results = list(engine_output.glob("*.obj"))
        if len(results) != 1:
            raise ValueError("OptCuts did not return exactly one mesh")
        with np.load(args.output / "geometry.npz") as mesh:
            corner_uv, transfer = transfer_uv(mesh["positions"], mesh["faces"], results[0])
        np.savez(args.output / "atlas.npz", corner_uv=corner_uv)
        (args.output / "transfer.json").write_text(json.dumps(transfer, indent=2), encoding="utf-8")
        subprocess.run(blender_command + ["--phase", "bake"], check=True)
        report = json.loads(report_path.read_text(encoding="utf-8"))
        if report.get("result") != "completed":
            raise ValueError(report.get("error", "UVgami bake failed"))
        if any(
            hashlib.sha256(Path(path).read_bytes()).hexdigest() != digest
            for path, digest in hashes.items()
        ):
            raise ValueError("Source artifacts changed during unwrap")
        report.update(engine=engine, transfer=transfer, protected_file_hashes=hashes)
    except Exception as error:
        report.update(result="failed", error=str(error))
        print(str(error), flush=True)
    finally:
        report["total_s"] = time.perf_counter() - started
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return 0 if report["result"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
