"""Isolated Blender remesh, UV, bake and export worker for static props."""
import argparse
import faulthandler
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import time
import traceback

import bmesh
import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from blender_geometry_quality import snapshot, evaluate, fill_microcracks


def select_only(obj):
    bpy.ops.object.select_all(action="DESELECT")
    obj.hide_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def mesh_stats(obj):
    mesh = obj.data
    mesh.calc_loop_triangles()
    bm = bmesh.new()
    bm.from_mesh(mesh)
    result = {
        "vertices": len(mesh.vertices),
        "triangles": len(mesh.loop_triangles),
        "faces": len(mesh.polygons),
        "boundary_edges": sum(edge.is_boundary for edge in bm.edges),
        "non_manifold_edges": sum(not edge.is_manifold for edge in bm.edges),
        "degenerate_faces": sum(face.calc_area() < 1e-12 for face in bm.faces),
        "dimensions": list(obj.dimensions),
    }
    bm.free()
    return result


def progress(output, stage):
    (output / "progress.json").write_text(
        json.dumps({"stage": stage, "time": time.time()}), encoding="utf-8"
    )
    print(f"STAGE: {stage}", flush=True)


def import_source(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(path))
    objects = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    if not objects:
        raise ValueError("GLB contains no mesh")
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    if len(objects) > 1:
        bpy.ops.object.join()
    source = bpy.context.view_layer.objects.active
    source.name = "Source_high"
    select_only(source)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    return source


def prepare_copy(source, output):
    low = source.copy()
    low.data = source.data.copy()
    bpy.context.collection.objects.link(low)
    low.name = "Remesh_low"
    select_only(low)
    bm = bmesh.new()
    bm.from_mesh(low.data)
    size = max(source.dimensions)
    weld_distance = max(size * 1e-7, 1e-9)
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=weld_distance)
    bmesh.ops.dissolve_degenerate(
        bm, edges=list(bm.edges), dist=weld_distance * 0.1
    )
    # Remove exact duplicate faces only; do not fill holes or delete small parts.
    bm.verts.index_update()
    seen = set()
    duplicates = []
    for face in bm.faces:
        key = tuple(sorted(vertex.index for vertex in face.verts))
        if key in seen:
            duplicates.append(face)
        else:
            seen.add(key)
    if duplicates:
        bmesh.ops.delete(bm, geom=duplicates, context="FACES_ONLY")
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(low.data)
    bm.free()
    low.data.update()
    low.data.materials.clear()
    while low.data.uv_layers:
        low.data.uv_layers.remove(low.data.uv_layers[0])
    return low, {
        "weld_distance": weld_distance,
        "exact_duplicate_faces_removed": len(duplicates),
        "holes_filled": False,
        "small_components_removed": False,
    }


def write_obj(obj, path):
    obj.data.calc_loop_triangles()
    with path.open("w", encoding="utf-8") as stream:
        for vertex in obj.data.vertices:
            position = obj.matrix_world @ vertex.co
            stream.write(f"v {position.x:.9g} {position.y:.9g} {position.z:.9g}\n")
        for face in obj.data.loop_triangles:
            indices = [index + 1 for index in face.vertices]
            stream.write("f " + " ".join(map(str, indices)) + "\n")


def remesh(low, args, output):
    faces = max(100, args.triangles // 2)
    if args.method == "meshopt":
        from blender_meshopt import reduce_mesh
        repair = fill_microcracks(low)
        settings = reduce_mesh(low, args, output)
        settings["repair"] = repair
        return low, settings
    if args.method == "simplify":
        select_only(low)
        repair = fill_microcracks(low)
        low.data.calc_loop_triangles()
        initial = len(low.data.loop_triangles)
        modifier = low.modifiers.new("Prepared surface simplification", "DECIMATE")
        ratio = min(1.0, args.triangles / initial)
        modifier.ratio = ratio
        modifier.use_collapse_triangulate = True
        bpy.ops.object.modifier_apply(modifier=modifier.name)
        return low, {"algorithm": "Blender Decimate after weld and limited microcrack repair",
                     "ratio": ratio,
                     "repair": repair}
    if args.method == "quadriflow":
        select_only(low)
        if args.voxel_repair:
            low.data.remesh_voxel_size = max(low.dimensions) / 300
            bpy.ops.object.voxel_remesh()
            bm = bmesh.new()
            bm.from_mesh(low.data)
            bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
            bm.to_mesh(low.data)
            bm.free()
            print("Voxel preparation:", json.dumps(mesh_stats(low)), flush=True)
        result = bpy.ops.object.quadriflow_remesh(
            use_mesh_symmetry=False,
            use_preserve_sharp=True,
            use_preserve_boundary=True,
            preserve_attributes=False,
            smooth_normals=False,
            mode="FACES",
            target_faces=faces,
            seed=args.seed,
        )
        if "FINISHED" not in result:
            raise RuntimeError(f"QuadriFlow did not finish: {result}")
        return low, {"target_quads": faces, "operator_result": sorted(result), "voxel_repair": args.voxel_repair, "voxel_resolution": 300 if args.voxel_repair else None}
    input_path = output / "remesh-input.obj"
    output_path = output / "remesh-output.obj"
    write_obj(low, input_path)
    command = [
        str(args.instant), str(input_path), "-o", str(output_path),
        "-f", str(faces), "-c", "45", "-b", "-d", "-D", "-t", str(args.threads),
    ]
    with (output / "instant-meshes.log").open("w", encoding="utf-8") as stream:
        result = subprocess.run(
            command, stdout=stream, stderr=subprocess.STDOUT, timeout=900,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    if result.returncode != 0 or not output_path.is_file():
        raise RuntimeError(
            f"Instant Meshes failed (exit {result.returncode}); see instant-meshes.log"
        )
    progress(output, "import_remesh")
    positions = []
    polygons = []
    with output_path.open(encoding="utf-8") as stream:
        for line in stream:
            fields = line.split()
            if fields and fields[0] == "v":
                positions.append(tuple(map(float, fields[1:4])))
            elif fields and fields[0] == "f":
                face = []
                for field in fields[1:]:
                    index = int(field.split("/")[0])
                    face.append(index - 1 if index > 0 else len(positions) + index)
                if len(set(face)) >= 3:
                    polygons.append(face)
    print("Parsed remesh", len(positions), len(polygons), flush=True)
    bpy.data.objects.remove(low, do_unlink=True)
    print("Removed copy", flush=True)
    mesh = bpy.data.meshes.new("Instant Meshes geometry")
    mesh.from_pydata(positions, [], polygons)
    print("Created remesh mesh", flush=True)
    mesh.update()
    low = bpy.data.objects.new("Remesh_low", mesh)
    bpy.context.collection.objects.link(low)
    select_only(low)
    return low, {"target_quads": faces, "command": command}


def create_uv(low, resolution, padding):
    select_only(low)
    modifier = low.modifiers.new("Final triangulation", "TRIANGULATE")
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    bm = bmesh.new()
    bm.from_mesh(low.data)
    invalid = [face for face in bm.faces if face.calc_area() < 1e-12]
    if invalid:
        bmesh.ops.delete(bm, geom=invalid, context="FACES")
    bm.to_mesh(low.data)
    bm.free()
    low.data.update()
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.002)
    bpy.ops.uv.average_islands_scale()
    # A large fixed fractional gap collapses densely fragmented atlases.
    # Scaled packing retains island area; raster diagnostics expose remaining limits.
    bpy.ops.uv.pack_islands(
        udim_source="ORIGINAL_AABB", rotate=True, scale=True,
        margin_method="SCALED", margin=0.002, shape_method="CONCAVE",
    )
    bpy.ops.object.mode_set(mode="OBJECT")
    for polygon in low.data.polygons:
        polygon.use_smooth = True
    coordinates = np.array([corner.uv[:] for corner in low.data.uv_layers.active.data])
    lower = coordinates.min(axis=0)
    upper = coordinates.max(axis=0)
    fitted = bool(np.any(lower < 0) or np.any(upper > 1))
    if fitted:
        # Uniformly fit the whole atlas; preserve island shapes and relative spacing.
        span = float((upper - lower).max())
        if span <= 0:
            raise ValueError("UV atlas has no extent")
        margin = padding / resolution
        scale = (1 - 2 * margin) / span
        for corner in low.data.uv_layers.active.data:
            corner.uv = (corner.uv - Vector(lower)) * scale + Vector((margin, margin))
    return {"atlas_fitted_to_unit_square": fitted,
            "bounds_before": {"min": lower.tolist(), "max": upper.tolist()}}


def uv_metrics(low, resolution):
    mesh = low.data
    mesh.calc_loop_triangles()
    uv_data = mesh.uv_layers.active.data
    # Raster coverage at a documented diagnostic resolution; exclude padding.
    diagnostic = min(resolution, 512)
    coverage = np.zeros((diagnostic, diagnostic), dtype=np.uint16)
    degenerate = 0
    for triangle in mesh.loop_triangles:
        coordinates = np.array([uv_data[index].uv[:] for index in triangle.loops])
        pixels = coordinates * diagnostic
        x0 = max(0, int(np.floor(pixels[:, 0].min())))
        x1 = min(diagnostic - 1, int(np.ceil(pixels[:, 0].max())))
        y0 = max(0, int(np.floor(pixels[:, 1].min())))
        y1 = min(diagnostic - 1, int(np.ceil(pixels[:, 1].max())))
        if x1 < x0 or y1 < y0:
            continue
        a, b, c = pixels
        denominator = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(denominator) < 1e-10:
            degenerate += 1
            continue
        yy, xx = np.mgrid[y0:y1 + 1, x0:x1 + 1]
        xx = xx + 0.5
        yy = yy + 0.5
        u = ((b[1] - c[1]) * (xx - c[0]) + (c[0] - b[0]) * (yy - c[1])) / denominator
        v = ((c[1] - a[1]) * (xx - c[0]) + (a[0] - c[0]) * (yy - c[1])) / denominator
        inside = (u >= 0) & (v >= 0) & ((u + v) <= 1)
        coverage[y0:y1 + 1, x0:x1 + 1] += inside.astype(np.uint16)
    coordinates = np.array([item.uv[:] for item in uv_data])
    return {
        "diagnostic_resolution": diagnostic,
        "coverage_fraction": float(np.mean(coverage > 0)),
        "overlap_pixel_fraction": float(np.mean(coverage > 1)),
        "outside_uv_corners": int(np.sum(np.any((coordinates < 0) | (coordinates > 1), axis=1))),
        "degenerate_uv_triangles": degenerate,
        "overlap_reason": "Sampled raster approximation; shared edges/subpixel overlaps not certified",
    }


def setup_material(low, resolution):
    material = bpy.data.materials.new("Baked game material")
    material.use_nodes = True
    low.data.materials.clear()
    low.data.materials.append(material)
    shader = material.node_tree.nodes.get("Principled BSDF")
    images = {}
    bake_nodes = {}
    for channel in ("base_color", "roughness", "metallic", "alpha", "normal"):
        image = bpy.data.images.new(channel, width=resolution, height=resolution)
        image.colorspace_settings.name = "sRGB" if channel == "base_color" else "Non-Color"
        image.generated_color = (0.5, 0.5, 1, 1) if channel == "normal" else (0, 0, 0, 1)
        node = material.node_tree.nodes.new("ShaderNodeTexImage")
        node.image = image
        node.label = channel
        images[channel] = image
        bake_nodes[channel] = node
    return material, shader, images, bake_nodes


def bake(source, low, args, output):
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 1
    scene.render.bake.use_selected_to_active = True
    scene.render.bake.use_clear = True
    scene.render.bake.margin = args.padding
    scene.render.bake.cage_extrusion = max(source.dimensions) * args.cage_ratio
    scene.render.bake.max_ray_distance = max(source.dimensions) * args.ray_ratio
    material, shader, images, targets = setup_material(low, args.texture)
    source.hide_render = False
    original_links = []
    source_materials = list({slot.material for slot in source.material_slots if slot.material})
    if not source_materials:
        raise ValueError("Source has no materials to bake")
    for source_material in source_materials:
        tree = source_material.node_tree
        output_node = next(node for node in tree.nodes if node.type == "OUTPUT_MATERIAL" and node.is_active_output)
        bsdf = next((node for node in tree.nodes if node.type == "BSDF_PRINCIPLED"), None)
        if bsdf is None:
            raise ValueError("Source material must have a Principled shader")
        old_socket = output_node.inputs["Surface"].links[0].from_socket
        emission = tree.nodes.new("ShaderNodeEmission")
        original_links.append((tree, output_node, old_socket, bsdf, emission))
    channel_inputs = {
        "base_color": "Base Color", "roughness": "Roughness",
        "metallic": "Metallic", "alpha": "Alpha",
    }
    for channel, input_name in channel_inputs.items():
        progress(output, "bake_" + channel)
        for tree, output_node, old_socket, bsdf, emission in original_links:
            for link in list(emission.inputs["Color"].links):
                tree.links.remove(link)
            socket = bsdf.inputs[input_name]
            if socket.is_linked:
                tree.links.new(socket.links[0].from_socket, emission.inputs["Color"])
            elif channel == "base_color":
                emission.inputs["Color"].default_value = socket.default_value
            else:
                value = socket.default_value
                emission.inputs["Color"].default_value = (value, value, value, 1)
            tree.links.new(emission.outputs[0], output_node.inputs["Surface"])
        select_only(low)
        source.select_set(True)
        material.node_tree.nodes.active = targets[channel]
        bpy.ops.object.bake(type="EMIT")
    for tree, output_node, old_socket, bsdf, emission in original_links:
        tree.links.new(old_socket, output_node.inputs["Surface"])
        tree.nodes.remove(emission)
    progress(output, "bake_normal")
    material.node_tree.nodes.active = targets["normal"]
    bpy.ops.object.bake(type="NORMAL", normal_space="TANGENT")
    for channel, image in images.items():
        image.filepath_raw = str(output / (channel + ".png"))
        image.file_format = "PNG"
        image.save()
        image.pack()
    links = material.node_tree.links
    opaque_source = all(
        not bsdf.inputs["Alpha"].is_linked and bsdf.inputs["Alpha"].default_value >= 0.999
        for tree, output_node, old_socket, bsdf, emission in original_links
    )
    shader.inputs["Alpha"].default_value = 1.0
    for channel, socket in (
        ("base_color", "Base Color"), ("roughness", "Roughness"),
        ("metallic", "Metallic"), ("alpha", "Alpha"),
    ):
        if channel == "alpha" and opaque_source:
            continue
        links.new(targets[channel].outputs["Color"], shader.inputs[socket])
    normal = material.node_tree.nodes.new("ShaderNodeNormalMap")
    links.new(targets["normal"].outputs["Color"], normal.inputs["Color"])
    links.new(normal.outputs["Normal"], shader.inputs["Normal"])
    # Match original opaque behavior; alpha map is available for manual glass setup.
    material.surface_render_method = "DITHERED"
    return images


def add_camera(source):
    scene = bpy.context.scene
    lower = Vector([min((source.matrix_world @ Vector(corner))[axis] for corner in source.bound_box) for axis in range(3)])
    upper = Vector([max((source.matrix_world @ Vector(corner))[axis] for corner in source.bound_box) for axis in range(3)])
    center = (lower + upper) / 2
    radius = max(upper - lower)
    data = bpy.data.cameras.new("Comparison camera")
    camera = bpy.data.objects.new("Comparison camera", data)
    scene.collection.objects.link(camera)
    data.type = "ORTHO"
    data.ortho_scale = radius * 1.6
    scene.camera = camera
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 12
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 512
    scene.render.resolution_y = 512
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = True
    scene.world = bpy.data.worlds.new("Comparison world")
    scene.world.use_nodes = True
    scene.world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.6
    for offset, energy in (((2, -3, 4), 450), ((-3, -1, 2), 220)):
        light_data = bpy.data.lights.new("Comparison light", "AREA")
        light_data.energy = energy * radius * radius
        light_data.size = radius * 3
        light = bpy.data.objects.new("Comparison light", light_data)
        scene.collection.objects.link(light)
        light.location = center + Vector(offset) * radius
        light.rotation_euler = (center - light.location).to_track_quat("-Z", "Y").to_euler()
    return camera, center, radius


def render_comparison(source, low, output):
    camera, center, radius = add_camera(source)
    scene = bpy.context.scene
    values = []
    for index, offset in enumerate(((1.7, -2.5, 1.45), (-1.7, 2.5, 1.2), (2.7, 0, 0.6), (0, 0, 3))):
        camera.location = center + Vector(offset) * radius
        camera.rotation_euler = (center - camera.location).to_track_quat("-Z", "Y").to_euler()
        masks = []
        for name, visible, hidden in (("original", source, low), ("optimized", low, source)):
            visible.hide_render = False
            hidden.hide_render = True
            scene.render.filepath = str(output / f"{name}-{index}.png")
            bpy.ops.render.render(write_still=True)
            result = bpy.data.images.load(scene.render.filepath, check_existing=False)
            pixels = np.array(result.pixels[:], dtype=np.float32).reshape(512, 512, 4)
            bpy.data.images.remove(result)
            masks.append(pixels[:, :, 3] > 0.5)
        union = np.sum(masks[0] | masks[1])
        values.append(float(np.sum(masks[0] & masks[1]) / union) if union else None)
    low.hide_render = False
    source.hide_render = True
    return values


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--method", choices=("quadriflow", "instant", "simplify", "meshopt"), required=True)
    parser.add_argument("--instant", type=Path)
    parser.add_argument("--meshopt-mode", choices=("position", "update", "normal-update"), default="update")
    parser.add_argument("--meshopt-error", type=float, default=.01)
    parser.add_argument("--triangles", type=int, default=12000)
    parser.add_argument("--texture", type=int, default=2048)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--threads", type=int, default=6)
    parser.add_argument("--padding", type=int, default=2)
    parser.add_argument("--cage-ratio", type=float, default=0.015)
    parser.add_argument("--ray-ratio", type=float, default=0.04)
    parser.add_argument("--remesh-only", action="store_true")
    parser.add_argument("--voxel-repair", action="store_true")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    args.output.mkdir(parents=True, exist_ok=True)
    faulthandler.dump_traceback_later(40, repeat=True)
    started = time.perf_counter()
    report = {
        "source": str(args.source), "method": args.method,
        "source_sha256": hashlib.sha256(args.source.read_bytes()).hexdigest(),
        "parameters": vars(args).copy(), "result": "failed",
        "stage_times_s": {},
    }
    report["parameters"] = {
        key: str(value) if isinstance(value, Path) else value
        for key, value in report["parameters"].items()
    }
    try:
        progress(args.output, "preparing")
        source = import_source(args.source)
        report["original"] = mesh_stats(source)
        source_snapshot = snapshot(source)
        low, preparation = prepare_copy(source, args.output)
        report["preparation"] = preparation
        report["prepared"] = mesh_stats(low)
        progress(args.output, "remesh")
        stage_start = time.perf_counter()
        low, settings = remesh(low, args, args.output)
        report["stage_times_s"]["remesh"] = time.perf_counter() - stage_start
        report["remesh_settings"] = settings
        progress(args.output, "cleanup_remesh")
        bm = bmesh.new()
        bm.from_mesh(low.data)
        invalid = [face for face in bm.faces if face.calc_area() < 1e-12]
        if invalid:
            bmesh.ops.delete(bm, geom=invalid, context="FACES")
        # Instant Meshes supplies oriented faces; Blender normal propagation stalls
        # on its mixed polygon output. Preserve that winding during cleanup.
        if args.method != "instant":
            bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
        bm.to_mesh(low.data)
        bm.free()
        low.data.update()
        report["degenerate_remesh_faces_removed"] = len(invalid)
        report["remeshed"] = mesh_stats(low)
        report["geometry_validation"] = evaluate(source_snapshot, low)
        if not report["geometry_validation"]["passed"]:
            raise RuntimeError("Remesh rejeitado: " + "; ".join(report["geometry_validation"]["failures"]))
        if args.remesh_only:
            select_only(low)
            bpy.ops.wm.save_as_mainfile(filepath=str(args.output / "remesh.blend"))
            report["result"] = "remeshed"
            return
        progress(args.output, "uv")
        stage_start = time.perf_counter()
        report["uv_preparation"] = create_uv(low, args.texture, args.padding)
        report["geometry_validation_after_triangulation"] = evaluate(source_snapshot, low)
        if not report["geometry_validation_after_triangulation"]["passed"]:
            raise RuntimeError("Malha rejeitada após triangulação: " + "; ".join(report["geometry_validation_after_triangulation"]["failures"]))
        report["uv"] = uv_metrics(low, args.texture)
        if report["uv"]["coverage_fraction"] < 0.01 or report["uv"]["outside_uv_corners"]:
            raise ValueError("UV atlas invalid: collapsed islands or coordinates outside 0-1")
        report["stage_times_s"]["uv"] = time.perf_counter() - stage_start
        progress(args.output, "bake")
        stage_start = time.perf_counter()
        bake(source, low, args, args.output)
        report["stage_times_s"]["bake"] = time.perf_counter() - stage_start
        progress(args.output, "export")
        select_only(low)
        bpy.ops.export_scene.gltf(
            filepath=str(args.output / "model.glb"), use_selection=True,
            export_format="GLB", export_image_format="AUTO",
            export_yup=True, export_tangents=True,
        )
        report["optimized"] = mesh_stats(low)
        report["triangle_reduction_fraction"] = 1 - report["optimized"]["triangles"] / report["original"]["triangles"]
        report["source_unchanged"] = hashlib.sha256(args.source.read_bytes()).hexdigest() == report["source_sha256"]
        progress(args.output, "comparison")
        report["render_alpha_iou_by_view"] = render_comparison(source, low, args.output)
        report["render_alpha_iou_note"] = "Four fixed views, alpha threshold 0.5; material transparency affects this metric"
        report["silhouette_reason"] = "Four sampled views; not an exact surface or hidden-feature guarantee"
        select_only(low)
        bpy.ops.wm.save_as_mainfile(filepath=str(args.output / "optimized.blend"))
        report["result"] = "completed"
        progress(args.output, "completed")
    except Exception as error:
        report["error"] = str(error)
        report["traceback"] = traceback.format_exc()
        print(report["traceback"], flush=True)
        progress(args.output, "failed")
    finally:
        report["total_s"] = time.perf_counter() - started
        (args.output / "report.json").write_text(
            json.dumps(report, indent=2), encoding="utf-8"
        )
    if report["result"] == "failed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
