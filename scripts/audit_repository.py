"""Fail before publication if tracked files include local data, secrets or large artifacts."""
import json
from pathlib import Path
import re
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_TOTAL_BYTES = 10 * 1024 * 1024
LOCAL_DIRECTORIES = {"runtime", "inputs", "outputs", "logs", "local_data", ".codex", ".aws"}
BINARY_SUFFIXES = {
    ".safetensors", ".ckpt", ".pth", ".pt", ".onnx", ".whl", ".zip",
    ".7z", ".exe", ".dll", ".pyd", ".glb", ".gltf", ".blend", ".npz", ".db",
}
SECRET_PATTERNS = (
    rb"gh[pousr]_[A-Za-z0-9]{20,}",
    rb"hf_[A-Za-z0-9]{20,}",
    rb"sk-proj-[A-Za-z0-9_-]{20,}",
    rb"AKIA[0-9A-Z]{16}",
    rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
)


def main():
    result = subprocess.run(
        ["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True,
    )
    names = [name.decode("utf-8") for name in result.stdout.split(b"\0") if name]
    if not names:
        raise RuntimeError("Nenhum arquivo no índice Git; prepare o índice antes de auditar.")
    failures = []
    inventory = []
    total = 0
    for name in names:
        relative = Path(name)
        if (
            relative.parts[0] in LOCAL_DIRECTORIES
            or "node_modules" in relative.parts
            or relative.parts[:2] == ("desktop", "dist")
            or relative.suffix.lower() in BINARY_SUFFIXES
            or relative.name.startswith(".env")
        ):
            failures.append({"file": name, "reason": "Local/private/heavy artifact tracked"})
        contents = subprocess.run(
            ["git", "show", f":{name}"], cwd=ROOT, capture_output=True, check=True,
        ).stdout
        total += len(contents)
        inventory.append({"file": name, "bytes": len(contents)})
        if len(contents) > MAX_FILE_BYTES:
            failures.append({"file": name, "reason": "File exceeds 5 MiB"})
        if relative.suffix.lower() not in (".png", ".ico"):
            if any(re.search(pattern, contents) for pattern in SECRET_PATTERNS):
                failures.append({"file": name, "reason": "Potential credential; inspect privately"})
    if total > MAX_TOTAL_BYTES:
        failures.append({"reason": "Tracked content exceeds 10 MiB"})
    report = {
        "ok": not failures,
        "files": len(names),
        "total_bytes": total,
        "largest_files": sorted(inventory, key=lambda item: item["bytes"], reverse=True)[:5],
        "failures": failures,
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
