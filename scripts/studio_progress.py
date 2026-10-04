"""Read real worker stages and local sampling iterations without overall estimates."""
import json
from pathlib import Path
import re


def tail(path, limit=16384):
    try:
        with Path(path).open("rb") as stream:
            stream.seek(0, 2)
            stream.seek(max(0, stream.tell() - limit))
            return stream.read().decode("utf-8", errors="replace")
    except OSError:
        return ""


def read_progress(directory, fallback="starting"):
    directory = Path(directory)
    stage = fallback
    try:
        data = json.loads((directory / "progress.json").read_text(encoding="utf-8"))
        stage = data["stage"]
    except (OSError, ValueError, KeyError):
        lines = tail(directory / "resources.csv", 4096).splitlines()
        for line in reversed(lines):
            values = line.split(",")
            if len(values) >= 8 and values[0] != "time_s":
                stage = values[1]
                break
    result = {"stage": stage, "iteration": None, "total": None}
    if stage in ("generate_and_preview", "generation", "running", "starting"):
        matches = list(re.finditer(
            r"(Sampling[^\r\n:]+):\s*\d+%[^\r\n]*?\|\s*(\d+)/(\d+)",
            tail(directory / "worker.log"),
        ))
        if matches:
            match = matches[-1]
            result = {"stage": match[1].strip(), "iteration": int(match[2]), "total": int(match[3])}
    return result


def stage_label(stage):
    labels = {
        "pending": "Na fila", "cancelled": "Cancelado", "generate": "Gerando modelo",
        "starting": "Iniciando processamento", "loading": "Carregando modelos",
        "preprocess": "Preparando imagem", "generate_and_preview": "Gerando modelo e prévias",
        "generation": "Gerando modelo", "running": "Processando",
        "export": "Preparando e exportando GLB", "shutdown": "Finalizando",
        "preparing": "Preparando a malha", "remesh": "Remesh automático",
        "import_remesh": "Importando remesh", "cleanup_remesh": "Limpando a malha",
        "uv": "Abrindo e organizando UV", "bake_base_color": "Bake de cor",
        "bake_roughness": "Bake de rugosidade", "bake_metallic": "Bake de metalicidade",
        "bake_alpha": "Bake de transparência", "bake_normal": "Bake de normais",
        "comparison": "Renderizando comparação", "completed": "Concluído",
        "failed": "Falhou", "interrupted": "Interrompido",
    }
    if stage.startswith("Sampling sparse"):
        return "Gerando estrutura 3D"
    if stage.startswith("Sampling shape"):
        return "Gerando geometria" + (" em alta resolução" if "HR" in stage else "")
    if stage.startswith("Sampling tex"):
        return "Gerando texturas"
    return labels.get(stage, stage)
