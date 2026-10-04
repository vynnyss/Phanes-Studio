"""Install the pinned upstream runtime without storing weights in Git."""
import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import urllib.request
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / "runtime/official/code"
SOURCES = json.loads((ROOT / "setup/sources.json").read_text(encoding="utf-8"))


def file_hash(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def download(url, destination, expected_hash):
    destination = Path(destination)
    if destination.exists():
        if file_hash(destination) != expected_hash:
            raise ValueError(f"SHA256 diferente do esperado: {destination}")
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(destination.suffix + ".download")
    print(f"Downloading {url}", flush=True)
    request = urllib.request.Request(url, headers={"User-Agent": "Phanes-Studio-Installer"})
    with urllib.request.urlopen(request, timeout=60) as response, partial.open("wb") as stream:
        shutil.copyfileobj(response, stream, 1024 * 1024)
    if file_hash(partial) != expected_hash:
        raise ValueError(f"Download rejeitado, SHA256 diferente: {url}")
    partial.replace(destination)


def extract_archive(archive, destination):
    destination = Path(destination).resolve()
    with ZipFile(archive) as package:
        for item in package.infolist():
            relative = item.filename.replace("\\", "/")
            target = (destination / relative).resolve()
            if not target.is_relative_to(destination) or ":" in relative:
                raise ValueError(f"Caminho inválido no ZIP: {item.filename}")
            if stat.S_ISLNK(item.external_attr >> 16):
                raise ValueError(f"Link simbólico não permitido: {item.filename}")
            if target.exists() and not item.is_dir():
                raise FileExistsError(f"Extração não sobrescreve arquivos existentes: {target}")
        package.extractall(destination)


def download_extra_models():
    models = CODE / "MODELS"
    for model in SOURCES["models"]:
        required = models / model["name"] / model["required_file"]
        if required.is_file():
            print(f"{model['name']} already available; preserving existing model.")
            continue
        archive = ROOT / "runtime/cache/setup" / (model["name"] + ".zip")
        download(model["url"], archive, model["sha256"])
        extract_archive(archive, models)
        if not required.is_file():
            raise FileNotFoundError(f"Modelo ausente após extração: {required}")


def download_huggingface_models():
    from huggingface_hub import snapshot_download

    cache = CODE / "models/hub"
    for model in SOURCES["huggingface"]:
        snapshot_download(
            repo_id=model["repo_id"],
            revision=model["revision"],
            cache_dir=str(cache),
        )
        # The upstream loader requests the main alias. Point it at the downloaded snapshot.
        repository_cache = cache / ("models--" + model["repo_id"].replace("/", "--"))
        reference = repository_cache / "refs/main"
        reference.parent.mkdir(parents=True, exist_ok=True)
        reference.write_text(model["revision"], encoding="utf-8")


def package_version(name):
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def upstream_available():
    distributions = (
        "torch", "torchvision", "torchaudio", "cumesh", "flex-gemm", "o-voxel",
        "nvdiffrast", "nvdiffrec-render", "utils3d", "xformers", "transformers",
        "huggingface_hub", "gradio", "trimesh",
    )
    return (
        package_version("torch") == "2.8.0+cu128"
        and all(package_version(name) for name in distributions)
    )


def studio_requirements_available():
    for line in (ROOT / "requirements-studio.txt").read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        name, expected = line.split("==")
        if package_version(name) != expected:
            return False
    return not package_version("opencv-python-headless") and not package_version("Pillow-SIMD")


def run_pip(*arguments):
    subprocess.run([sys.executable, "-m", "pip", *arguments], check=True)


def install_optional_tools():
    instant = SOURCES["instant_meshes"]
    directory = ROOT / "runtime/tools/instant-meshes/bin"
    if not (directory / "Instant Meshes.exe").is_file():
        archive = ROOT / "runtime/cache/setup/instant-meshes-windows.zip"
        download(instant["url"], archive, instant["sha256"])
        extract_archive(archive, directory)
    shutil.copyfile(ROOT / "licenses/INSTANT-MESHES.txt", directory.parent / "LICENSE.txt")
    xatlas = ROOT / "runtime/tools/xatlas-python"
    if not list(xatlas.glob("xatlas*.pyd")):
        run_pip("install", "xatlas==0.0.11", "--target", str(xatlas))


def check_installation():
    os.environ["OPENCV_IO_ENABLE_OPENEXR"] = "1"
    import cv2
    import numpy as np
    import torch
    from PIL import Image
    import fastapi
    import gradio
    import psutil
    import requests
    import uvicorn

    # Check actual extensions, not merely installed distribution metadata.
    sys.path.insert(0, str(CODE))
    import cumesh
    import flex_gemm
    import o_voxel
    import nvdiffrast.torch
    import nvdiffrec_render

    environment = cv2.imread(str(CODE / "assets/hdri/forest.exr"), cv2.IMREAD_UNCHANGED)
    if environment is None:
        raise RuntimeError("OpenEXR indisponível; forest.exr não pôde ser carregado.")
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA indisponível. Verifique o driver NVIDIA e a GPU.")
    missing_models = []
    for model in SOURCES["models"]:
        if not (CODE / "MODELS" / model["name"] / model["required_file"]).is_file():
            missing_models.append(model["name"])
    for model in SOURCES["huggingface"]:
        cached = CODE / "models/hub" / ("models--" + model["repo_id"].replace("/", "--"))
        if not (cached / "snapshots" / model["revision"] / "pipeline.json").is_file():
            missing_models.append(model["repo_id"])
    return {
        "ok": not missing_models,
        "python": sys.version.split()[0],
        "torch": torch.__version__,
        "cuda": torch.version.cuda,
        "gpu": torch.cuda.get_device_name(),
        "openexr": True,
        "missing_models": missing_models,
        "desktop": (ROOT / "desktop/dist/3DStudio/Phanes Studio.exe").is_file(),
        "meshoptimizer": (ROOT / "runtime/tools/meshoptimizer/meshopt_simplifier.js").is_file(),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--skip-models", action="store_true")
    parser.add_argument("--optional-tools", action="store_true")
    arguments = parser.parse_args()
    if sys.version_info[:2] != (3, 11):
        raise RuntimeError("O runtime Windows exige Python 3.11 para seus wheels.")
    if arguments.check:
        report = check_installation()
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0 if report["ok"] and report["desktop"] and report["meshoptimizer"] else 1

    os.chdir(CODE)
    sys.path.insert(0, str(CODE))
    os.environ["HF_HOME"] = str(CODE / "models")
    os.environ["GRADIO_ANALYTICS_ENABLED"] = "False"
    specification = importlib.util.spec_from_file_location("upstream_installer", CODE / "install.py")
    upstream = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(upstream)
    if arguments.skip_models:
        upstream.download_models = lambda: print("Extra models skipped by request.")
        upstream.download_hf_models = lambda: print("Hugging Face models skipped by request.")
    else:
        upstream.download_models = download_extra_models
        upstream.download_hf_models = download_huggingface_models
    if not upstream_available():
        upstream.install_dependencies()
    elif not arguments.skip_models:
        download_extra_models()
        download_huggingface_models()
    if not studio_requirements_available():
        run_pip("uninstall", "-y", "opencv-python", "opencv-python-headless", "Pillow-SIMD")
        run_pip("install", "-r", str(ROOT / "requirements-studio.txt"))
    if arguments.optional_tools:
        install_optional_tools()
    run_pip("check")
    report = check_installation()
    if report["missing_models"] and not arguments.skip_models:
        raise RuntimeError(f"Modelos ausentes: {report['missing_models']}")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"Installation failed: {error}", file=sys.stderr)
        raise SystemExit(1)
