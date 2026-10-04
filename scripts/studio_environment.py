"""Paths and child-process environment for the local Studio installation."""
import os
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def configure_environment(root=None):
    root = Path(root or os.environ.get("STUDIO_ROOT", PROJECT_ROOT)).resolve()
    code = root / "runtime/official/code"
    temporary = root / "runtime/temp"
    temporary.mkdir(parents=True, exist_ok=True)
    for directory in ("inputs", "outputs", "logs", "local_data/studio"):
        (root / directory).mkdir(parents=True, exist_ok=True)
    values = {
        "STUDIO_ROOT": str(root),
        "HF_HOME": str(code / "models"),
        "GRADIO_TEMP_DIR": str(temporary / "gradio"),
        "TEMP": str(temporary),
        "TMP": str(temporary),
        "PYTHONNOUSERSITE": "1",
        "PYTHONUTF8": "1",
        "SETUPTOOLS_USE_DISTUTILS": "stdlib",
        "TORCH_HOME": str(root / "runtime/cache/torch"),
        "TRITON_CACHE_DIR": str(root / "runtime/cache/triton"),
        "CUDA_CACHE_PATH": str(root / "runtime/cache/cuda"),
        "SPARSE_DEBUG": "0",
        "GRADIO_ANALYTICS_ENABLED": "False",
    }
    os.environ.update(values)
    settings_file = root / "local_data/settings.json"
    if settings_file.is_file() and not os.environ.get("ASSET_BLENDER"):
        settings = json.loads(settings_file.read_text(encoding="utf-8"))
        if settings.get("blender"):
            os.environ["ASSET_BLENDER"] = str(settings["blender"])
    return root


def python_path(root):
    return Path(os.environ.get(
        "STUDIO_PYTHON", str(Path(root) / "runtime/official/code/venv/Scripts/python.exe")
    ))
