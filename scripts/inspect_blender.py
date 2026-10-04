import argparse
import json
import math
from pathlib import Path
import sys

import bpy
import bmesh
from mathutils import Vector


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--glb', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    argv = sys.argv[sys.argv.index('--') + 1:]
    args = parser.parse_args(argv)
    args.output.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(args.glb))
    objects = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
    report = {'source': str(args.glb), 'imported': True, 'meshes': [], 'materials': []}
    for obj in objects:
        mesh = obj.data
        mesh.calc_loop_triangles()
        copy = bmesh.new()
        copy.from_mesh(mesh)
        bmesh.ops.remove_doubles(copy, verts=list(copy.verts), dist=1e-6)
        copy.verts.ensure_lookup_table()
        seen = set()
        components = []
        for vertex in copy.verts:
            if vertex.index in seen:
                continue
            stack = [vertex]
            seen.add(vertex.index)
            size = 0
            while stack:
                current = stack.pop()
                size += 1
                for edge in current.link_edges:
                    neighbor = edge.other_vert(current)
                    if neighbor.index not in seen:
                        seen.add(neighbor.index)
                        stack.append(neighbor)
            components.append(size)
        report['meshes'].append({
            'object': obj.name,
            'vertices_glb': len(mesh.vertices),
            'faces': len(mesh.polygons),
            'triangles': len(mesh.loop_triangles),
            'uv_layers': len(mesh.uv_layers),
            'welded_vertices': len(copy.verts),
            'welded_connected_components': len(components),
            'largest_component_vertices': max(components, default=0),
            'welded_boundary_edges': sum(edge.is_boundary for edge in copy.edges),
            'welded_non_manifold_edges': sum(not edge.is_manifold for edge in copy.edges),
            'degenerate_faces': sum(face.calc_area() < 1e-12 for face in copy.faces),
            'finite_positions': all(math.isfinite(value) for vertex in mesh.vertices for value in vertex.co),
            'finite_vertex_normals': all(math.isfinite(value) for vertex in mesh.vertices for value in vertex.normal),
            'dimensions': list(obj.dimensions),
            'scale': list(obj.scale),
        })
        copy.free()
    for material in bpy.data.materials:
        maps = []
        if material.node_tree:
            for node in material.node_tree.nodes:
                if node.type == 'TEX_IMAGE' and node.image:
                    maps.append({
                        'name': node.image.name,
                        'size': list(node.image.size),
                        'has_data': node.image.has_data,
                        'packed': node.image.packed_file is not None,
                    })
        report['materials'].append({'name': material.name, 'use_nodes': material.use_nodes, 'maps': maps})
    scene = bpy.context.scene
    scene.unit_settings.system = 'METRIC'
    # The model stays unchanged; camera and lights are derived inspection aids.
    points = [obj.matrix_world @ Vector(corner) for obj in objects for corner in obj.bound_box]
    lower = Vector([min(point[axis] for point in points) for axis in range(3)])
    upper = Vector([max(point[axis] for point in points) for axis in range(3)])
    center = (lower + upper) / 2
    radius = max(upper - lower)
    camera_data = bpy.data.cameras.new('InspectionCamera')
    camera = bpy.data.objects.new('InspectionCamera', camera_data)
    scene.collection.objects.link(camera)
    camera.location = center + Vector((1.7, -2.5, 1.45)) * radius
    camera.rotation_euler = (center - camera.location).to_track_quat('-Z', 'Y').to_euler()
    camera_data.type = 'ORTHO'
    camera_data.ortho_scale = radius * 1.65
    scene.camera = camera
    scene.world = bpy.data.worlds.new('InspectionWorld')
    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes.get('Background')
    background.inputs['Color'].default_value = (0.2, 0.2, 0.2, 1)
    background.inputs['Strength'].default_value = 0.7
    for name, offset, energy, size in [
        ('Key', (2, -3, 4), 500, 4),
        ('Fill', (-3, -1, 2), 250, 3),
        ('Rim', (1, 3, 3), 400, 3),
    ]:
        data = bpy.data.lights.new(name, type='AREA')
        data.energy = energy * radius * radius
        data.shape = 'DISK'
        data.size = size * radius
        light = bpy.data.objects.new(name, data)
        scene.collection.objects.link(light)
        light.location = center + Vector(offset) * radius
        light.rotation_euler = (center - light.location).to_track_quat('-Z', 'Y').to_euler()
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 24
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 640
    scene.render.resolution_y = 640
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.view_settings.view_transform = 'AgX'
    scene.render.filepath = str(args.output / 'blender-render.png')
    bpy.ops.wm.save_as_mainfile(filepath=str(args.output / 'inspection.blend'))
    bpy.ops.render.render(write_still=True)
    report['render'] = str(args.output / 'blender-render.png')
    report['blend'] = str(args.output / 'inspection.blend')
    report['normals_visual_review'] = 'pending'
    report['internal_geometry'] = None
    report['internal_geometry_reason'] = 'requires cross-section/manual review; component count alone insufficient'
    (args.output / 'blender-report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
