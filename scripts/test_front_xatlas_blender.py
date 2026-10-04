"""UV-only experiment on the approved front LOW; no remeshing."""
import argparse
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import sys
import time

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from blender_asset_worker import bake, mesh_stats, render_comparison, select_only, uv_metrics

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "outputs/remesh-diagnosis/front/simplify-baked"
OUTPUT = ROOT / "outputs/uv-xatlas/front"
parser = argparse.ArgumentParser()
parser.add_argument("mode", choices=["extract", "bake"])
parser.add_argument("--output", type=Path, default=OUTPUT)
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
OUTPUT = args.output
bpy.ops.wm.open_mainfile(filepath=str(BASE / "optimized.blend"))
source = bpy.data.objects["Source_high"]
low = next(obj for obj in bpy.context.scene.objects if obj.type == "MESH" and obj != source)
low.data.calc_loop_triangles()
positions = np.array([vertex.co[:] for vertex in low.data.vertices], dtype=np.float32)
faces = np.array([tri.vertices[:] for tri in low.data.loop_triangles], dtype=np.uint32)
loops = np.array([tri.loops[:] for tri in low.data.loop_triangles])
geometry_hash = hashlib.sha256(positions.tobytes() + faces.tobytes()).hexdigest()
if args.mode == "extract":
    np.savez(OUTPUT / "approved-geometry.npz", positions=positions, faces=faces)
    (OUTPUT / "baseline.json").write_text(json.dumps({
        "geometry_sha256": geometry_hash,
        "uv": uv_metrics(low, 1024),
        "mesh": mesh_stats(low),
    }, indent=2))
else:
    started = time.perf_counter()
    atlas = np.load(OUTPUT / "atlas.npz")
    assert np.array_equal(atlas["faces"], faces), "Face correspondence changed"
    corner_uv = atlas["corner_uv"]
    assert np.isfinite(corner_uv).all()
    layer = low.data.uv_layers.active
    for triangle_loops, coordinates in zip(loops, corner_uv):
        for loop_index, uv in zip(triangle_loops, coordinates):
            layer.data[int(loop_index)].uv = uv
    for obj in bpy.context.scene.objects:
        if obj.type in ("LIGHT", "CAMERA"):
            bpy.data.objects.remove(obj, do_unlink=True)
    low.hide_set(False)
    source.hide_set(False)
    settings = SimpleNamespace(texture=1024, padding=2, cage_ratio=.015, ray_ratio=.04)
    report = {
        "method": "xatlas-uv-only",
        "triangles": len(faces),
        "geometry_sha256_before": geometry_hash,
        "uv": uv_metrics(low, 1024),
        "xatlas": json.loads((OUTPUT / "atlas-report.json").read_text()),
    }
    assert report["uv"]["outside_uv_corners"] == 0
    assert report["uv"]["degenerate_uv_triangles"] == 0
    assert report["uv"]["overlap_pixel_fraction"] < .001
    bake(source, low, settings, OUTPUT)
    select_only(low)
    bpy.ops.export_scene.gltf(
        filepath=str(OUTPUT / "model.glb"), use_selection=True,
        export_format="GLB", export_image_format="AUTO", export_yup=True,
        export_tangents=True,
    )
    report["render_alpha_iou_by_view"] = render_comparison(source, low, OUTPUT)
    current_positions = np.array([v.co[:] for v in low.data.vertices], dtype=np.float32)
    low.data.calc_loop_triangles()
    current_faces = np.array([t.vertices[:] for t in low.data.loop_triangles], dtype=np.uint32)
    report["geometry_unchanged"] = (
        np.array_equal(positions, current_positions) and np.array_equal(faces, current_faces)
    )
    assert report["geometry_unchanged"]
    report["optimized"] = mesh_stats(low)
    report["total_s"] = time.perf_counter() - started
    report["result"] = "completed"
    select_only(low)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT / "optimized.blend"))
    (OUTPUT / "report.json").write_text(json.dumps(report, indent=2))
