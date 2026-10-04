"""Geometric rejection checks; no arbitrary aggregate quality score."""
import bmesh
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree


def snapshot(obj):
    mesh = obj.data
    mesh.calc_loop_triangles()
    positions = np.array([obj.matrix_world @ vertex.co for vertex in mesh.vertices])
    indices = np.array([triangle.vertices[:] for triangle in mesh.loop_triangles])
    triangles = positions[indices]
    areas = np.linalg.norm(np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0]), axis=1) * .5
    if not areas.sum():
        raise ValueError("Malha sem superfície válida")
    diagonal = float(np.linalg.norm(np.ptp(positions, axis=0)))
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=max(diagonal * 1e-7, 1e-9))
    boundary = [edge for edge in bm.edges if edge.is_boundary]
    metrics = {
        "boundary_edges": len(boundary),
        "boundary_length": sum(edge.calc_length() for edge in boundary),
        "surface_area": float(areas.sum()),
        "diagonal": diagonal,
    }
    bm.free()
    rng = np.random.default_rng(0)
    chosen = rng.choice(len(triangles), 2000, p=areas / areas.sum())
    u = np.sqrt(rng.random((2000, 1)))
    v = rng.random((2000, 1))
    samples = (
        (1 - u) * triangles[chosen, 0]
        + u * (1 - v) * triangles[chosen, 1]
        + u * v * triangles[chosen, 2]
    )
    tree = BVHTree.FromPolygons([Vector(p) for p in positions], indices.tolist(), all_triangles=True)
    return {"metrics": metrics, "samples": samples, "tree": tree}


def evaluate(source, candidate):
    candidate = snapshot(candidate)
    metrics = dict(candidate["metrics"])
    diagonal = source["metrics"]["diagonal"]
    failures = []
    limits = {
        "boundary_length": source["metrics"]["boundary_length"] * 1.25 + diagonal * .02,
        "distance_p95_relative": .01,
        "distance_max_relative": .05,
    }
    if metrics["boundary_length"] > limits["boundary_length"]:
        failures.append("novas fissuras/buracos: comprimento de bordas abertas excede o limite")
    for name, points, tree in (
        ("source_to_candidate", source["samples"], candidate["tree"]),
        ("candidate_to_source", candidate["samples"], source["tree"]),
    ):
        distances = np.array([tree.find_nearest(Vector(point))[3] for point in points]) / diagonal
        metrics[name] = {"p95_relative": float(np.quantile(distances,.95)),
                         "max_relative": float(distances.max())}
        exceeds_p95 = metrics[name]["p95_relative"] > limits["distance_p95_relative"]
        exceeds_max = metrics[name]["max_relative"] > limits["distance_max_relative"]
        if exceeds_p95 or exceeds_max:
            failures.append("desvio de superfície acima do limite: " + name)
    return {
        "passed": not failures,
        "source": source["metrics"],
        "candidate": metrics,
        "limits": limits,
        "failures": failures,
        "samples_per_direction": 2000,
        "limitation": "Sampled distances and boundary length do not certify all topology or hidden features",
    }


def fill_microcracks(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    remaining = {edge for edge in bm.edges if edge.is_boundary}
    limit = max(obj.dimensions) * .025
    loops = 0
    new_faces = 0
    while remaining:
        seed = remaining.pop()
        component = {seed}
        pending = [seed]
        while pending:
            edge = pending.pop()
            for vertex in edge.verts:
                for adjacent in vertex.link_edges:
                    if adjacent in remaining:
                        remaining.remove(adjacent)
                        component.add(adjacent)
                        pending.append(adjacent)
        vertices = {vertex for edge in component for vertex in edge.verts}
        closed_loop = all(sum(edge in component for edge in vertex.link_edges)==2 for vertex in vertices)
        perimeter = sum(edge.calc_length() for edge in component)
        if closed_loop and len(vertices) <= 8 and perimeter <= limit:
            faces = bmesh.ops.holes_fill(bm, edges=list(component), sides=0)["faces"]
            loops += bool(faces)
            new_faces += len(faces)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    return {"small_loops_filled": loops, "new_faces": new_faces,
            "max_loop_vertices": 8, "max_loop_perimeter": limit}
