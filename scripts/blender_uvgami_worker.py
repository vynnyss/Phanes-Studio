"""Open a LOW bake scene, change its UVs, and rebake without remeshing."""
import argparse
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from blender_asset_worker import bake, mesh_stats, progress, render_comparison, select_only, uv_metrics


def geometry(obj):
    obj.data.calc_loop_triangles()
    return (
        np.array([vertex.co[:] for vertex in obj.data.vertices], dtype=np.float32),
        np.array([tri.vertices[:] for tri in obj.data.loop_triangles], dtype=np.uint32),
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--texture", type=int, required=True)
    parser.add_argument("--phase", choices=("prepare", "bake"), required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    bpy.ops.wm.open_mainfile(filepath=str(args.source))
    source = bpy.data.objects.get("Source_high")
    candidates = [obj for obj in bpy.context.scene.objects if obj.type == "MESH" and obj != source]
    if source is None or len(candidates) != 1:
        raise ValueError("UVgami requires a LOW bake scene containing one LOW and Source_high")
    low = candidates[0]
    if low.modifiers or any(len(face.vertices) != 3 for face in low.data.polygons):
        raise ValueError("UV-only transfer requires a triangulated LOW without modifiers")
    positions, faces = geometry(low)
    if args.phase == "prepare":
        progress(args.output, "uv")
        np.savez(args.output / "geometry.npz", positions=positions, faces=faces)
        with (args.output / "low.obj").open("w", encoding="utf-8") as stream:
            for position in positions:
                stream.write("v %.12g %.12g %.12g\n" % tuple(position))
            for face in faces:
                stream.write("f %d %d %d\n" % tuple(face + 1))
        return
    with np.load(args.output / "geometry.npz") as original:
        if (
            not np.array_equal(positions, original["positions"])
            or not np.array_equal(faces, original["faces"])
        ):
            raise ValueError("LOW changed between export and UV transfer")
    baseline = uv_metrics(low, args.texture)
    with np.load(args.output / "atlas.npz") as atlas:
        corner_uv = atlas["corner_uv"]
    if corner_uv.shape != (len(faces), 3, 2) or not np.isfinite(corner_uv).all():
        raise ValueError("Invalid corner UV atlas")
    layer = low.data.uv_layers.active or low.data.uv_layers.new(name="UVMap")
    for triangle, coords in zip(low.data.loop_triangles, corner_uv):
        for loop, uv in zip(triangle.loops, coords):
            layer.data[loop].uv = uv
    select_only(low)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.select_all(action="SELECT")
    bpy.ops.uv.average_islands_scale()
    bpy.ops.uv.pack_islands(
        rotate=True, rotate_method="AXIS_ALIGNED", scale=True,
        margin_method="FRACTION", margin=4 / args.texture,
        shape_method="CONCAVE", udim_source="CLOSEST_UDIM",
    )
    bpy.ops.object.mode_set(mode="OBJECT")
    uv = uv_metrics(low, args.texture)
    if (
        uv["outside_uv_corners"]
        or uv["degenerate_uv_triangles"]
        or uv["overlap_pixel_fraction"] >= .001
    ):
        raise ValueError("Invalid UV packing; bake refused")
    for obj in list(bpy.context.scene.objects):
        if obj.type in ("LIGHT", "CAMERA"):
            bpy.data.objects.remove(obj, do_unlink=True)
    settings = SimpleNamespace(texture=args.texture, padding=2, cage_ratio=.015, ray_ratio=.04)
    low.hide_set(False)
    source.hide_set(False)
    bake(source, low, settings, args.output)
    progress(args.output, "export")
    select_only(low)
    bpy.ops.export_scene.gltf(
        filepath=str(args.output / "model.glb"), use_selection=True,
        export_format="GLB", export_image_format="AUTO", export_yup=True,
        export_tangents=True,
    )
    progress(args.output, "comparison")
    comparison = render_comparison(source, low, args.output)
    after_positions, after_faces = geometry(low)
    if not np.array_equal(positions, after_positions) or not np.array_equal(faces, after_faces):
        raise ValueError("Geometry changed during UV-only bake")
    select_only(low)
    bpy.ops.wm.save_as_mainfile(filepath=str(args.output / "optimized.blend"))
    report = {
        "result": "completed",
        "method": "uvgami-optcuts",
        "geometry_unchanged": True,
        "baseline": {"uv": baseline},
        "uv": uv,
        "optimized": mesh_stats(low),
        "bake": vars(settings),
        "render_alpha_iou_by_view": comparison,
        "quality_status": "unreviewed",
    }
    (args.output / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    progress(args.output, "completed")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(1)
