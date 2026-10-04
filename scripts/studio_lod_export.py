"""Export explicit reviewed candidate selections into a new, self-contained LOD folder."""
import hashlib
import json
from pathlib import Path
import shutil
import uuid


def triangle_count(model):
    if not model.get("report"):
        raise ValueError("Modelo sem relatório de triângulos")
    report = json.loads(Path(model["report"]).read_text(encoding="utf-8-sig"))
    count = report.get("triangles") or report.get("optimized", {}).get("triangles")
    if not isinstance(count, int) or count <= 0:
        raise ValueError("Contagem de triângulos indisponível")
    return count


def export_lods(studio, variant_ids, target_directory):
    if not variant_ids or len(variant_ids) > 8 or len(set(variant_ids)) != len(variant_ids):
        raise ValueError("Selecione de 1 a 8 versões, sem duplicatas")
    destination = Path(target_directory).expanduser()
    if not destination.is_absolute():
        raise ValueError("Informe uma pasta de destino absoluta")
    destination = destination.resolve()
    if destination.exists() and not destination.is_dir():
        raise ValueError("O destino deve ser uma pasta")
    models = [studio.variant(identifier) for identifier in variant_ids]
    if len({model["asset_id"] for model in models}) != 1:
        raise ValueError("Todos os LODs devem pertencer ao mesmo modelo original")
    if any(model.get("quality_status") == "rejected" for model in models):
        raise ValueError("Versões rejeitadas não podem ser exportadas como LOD")
    levels = sorted([(triangle_count(model), model) for model in models],
                    key=lambda item: (-item[0], item[1]["id"]))
    counts = [count for count, model in levels]
    if len(set(counts)) != len(counts):
        raise ValueError("Escolha uma versão por nível; contagens de triângulos devem ser diferentes")
    destination.mkdir(parents=True, exist_ok=True)
    export_id = uuid.uuid4().hex
    final = destination / ("lods-" + models[0]["asset_id"][:8] + "-" + export_id[:12])
    staging = destination / (".lods-partial-" + export_id)
    manifest = {
        "export_id": export_id,
        "asset_id": models[0]["asset_id"],
        "format": "separate GLB files with embedded textures",
        "levels": [],
        "switch_distances": None,
        "switch_distances_reason": "Configure in the game engine after manual visual review",
        "approval_note": "Exporting does not approve unreviewed candidates",
    }
    staging.mkdir()
    try:
        for index, (count, model) in enumerate(levels):
            source = Path(model["model"])
            with source.open("rb") as stream:
                header = stream.read(12)
            if header[:4] != b"glTF" or int.from_bytes(header[8:12], "little") != source.stat().st_size:
                raise ValueError("GLB inválido: " + model["name"])
            filename = f"LOD{index}.glb"
            shutil.copy2(source, staging / filename)
            digest = hashlib.sha256((staging / filename).read_bytes()).hexdigest()
            if digest != hashlib.sha256(source.read_bytes()).hexdigest():
                raise OSError("Export verification failed")
            report_name = f"LOD{index}-report.json"
            shutil.copy2(model["report"], staging / report_name)
            manifest["levels"].append({
                "level": index, "file": filename, "report": report_name,
                "variant_id": model["id"], "name": model["name"],
                "triangles": count, "sha256": digest,
                "quality_status": model.get("quality_status", "unreviewed"),
            })
        (staging / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        staging.rename(final)
    except Exception:
        # Only remove this export's resolved private staging folder, inside destination.
        resolved = staging.resolve()
        if resolved.parent == destination and resolved.name == ".lods-partial-" + export_id:
            shutil.rmtree(resolved, ignore_errors=True)
        raise
    return {"export_id": export_id, "directory": str(final),
            "manifest": str(final / "manifest.json"), "levels": manifest["levels"]}
