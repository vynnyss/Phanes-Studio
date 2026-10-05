"""Transfer only UV corners from OptCuts back onto the unchanged LOW."""
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree


def transfer_uv(positions, faces, engine_obj):
    vertices, uvs, triangles, uv_faces = [], [], [], []
    for line in Path(engine_obj).read_text(encoding="utf-8").splitlines():
        fields = line.split()
        if not fields:
            continue
        if fields[0] == "v":
            vertices.append([float(value) for value in fields[1:4]])
        elif fields[0] == "vt":
            uvs.append([float(value) for value in fields[1:3]])
        elif fields[0] == "f":
            if len(fields) != 4:
                raise ValueError("OptCuts returned a non-triangular face")
            corners = [field.split("/") for field in fields[1:]]
            triangles.append([int(corner[0]) - 1 for corner in corners])
            uv_faces.append([int(corner[1]) - 1 for corner in corners])
    vertices = np.asarray(vertices)
    uvs = np.asarray(uvs)
    triangles = np.asarray(triangles)
    uv_faces = np.asarray(uv_faces)
    if not vertices.size or len(triangles) != len(faces) or not uvs.size:
        raise ValueError("OptCuts returned an incomplete mesh")
    if not np.isfinite(vertices).all() or not np.isfinite(uvs).all():
        raise ValueError("OptCuts returned non-finite coordinates")
    if (
        triangles.min() < 0
        or triangles.max() >= len(vertices)
        or uv_faces.min() < 0
        or uv_faces.max() >= len(uvs)
    ):
        raise ValueError("OptCuts returned invalid OBJ indices")
    distance, mapping = cKDTree(positions).query(vertices)
    if distance.max() >= 2e-6:
        raise ValueError("OptCuts moved or added surface vertices")
    lookup = {}
    for index, face in enumerate(faces):
        key = tuple(sorted(face))
        if key in lookup:
            raise ValueError("LOW contains ambiguous duplicate triangles")
        lookup[key] = index
    corner_uv = np.full((len(faces), 3, 2), np.nan)
    seen = set()
    for triangle, uv_face in zip(triangles, uv_faces):
        mapped = mapping[triangle]
        key = tuple(sorted(mapped))
        if key not in lookup or lookup[key] in seen:
            raise ValueError("OptCuts changed triangle connectivity")
        index = lookup[key]
        seen.add(index)
        for corner, vertex in enumerate(faces[index]):
            match = np.flatnonzero(mapped == vertex)
            if len(match) != 1:
                raise ValueError("Ambiguous vertex correspondence")
            corner_uv[index, corner] = uvs[uv_face[match[0]]]
    if len(seen) != len(faces) or not np.isfinite(corner_uv).all():
        raise ValueError("Not all original triangle corners were matched")
    return corner_uv, {
        "all_original_triangles_matched": True,
        "triangle_count": len(faces),
        "maximum_serialization_position_error": float(distance.max()),
        "transfer": "Only original triangle corner UVs; original coordinates retained",
    }
