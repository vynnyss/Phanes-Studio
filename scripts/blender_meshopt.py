"""Blender adapter for the audited, local meshoptimizer simplifier."""
import json
from pathlib import Path
import subprocess

import bpy

ROOT = Path(__file__).resolve().parents[1]


def reduce_mesh(obj, args, output):
    mesh = obj.data
    mesh.calc_loop_triangles()
    source_path = output / "meshopt-input.json"
    result_path = output / "meshopt-output.json"
    source_path.write_text(json.dumps({
        "positions": [value for vertex in mesh.vertices for value in vertex.co],
        "indices": [index for triangle in mesh.loop_triangles for index in triangle.vertices],
        "normals": [value for vertex in mesh.vertices for value in vertex.normal],
    }))
    command = [
        str(ROOT / "runtime/tools/meshoptimizer/node.exe"),
        str(ROOT / "scripts/meshopt_reduce.cjs"), str(source_path), str(result_path),
        str(args.triangles), args.meshopt_mode, str(args.meshopt_error),
    ]
    subprocess.run(command, check=True, timeout=300, capture_output=True, text=True)
    result = json.loads(result_path.read_text())
    coordinates = result.pop("positions")
    indices = result.pop("indices")
    used = sorted(set(indices))
    mapping = {original: compact for compact, original in enumerate(used)}
    vertices = [coordinates[index * 3:index * 3 + 3] for index in used]
    faces = [
        [mapping[index] for index in indices[offset:offset + 3]]
        for offset in range(0, len(indices), 3)
    ]
    new_mesh = bpy.data.meshes.new("Meshoptimizer surface")
    new_mesh.from_pydata(vertices, [], faces)
    new_mesh.update()
    old_mesh = obj.data
    obj.data = new_mesh
    if old_mesh.users == 0:
        bpy.data.meshes.remove(old_mesh)
    return result
