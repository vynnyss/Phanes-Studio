import argparse
from pathlib import Path
import sys

import bpy
import bmesh
from mathutils import Vector

parser = argparse.ArgumentParser()
parser.add_argument('--glb', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(args.glb))
scene = bpy.context.scene
objects = [obj for obj in scene.objects if obj.type == 'MESH']
points = [obj.matrix_world @ Vector(corner) for obj in objects for corner in obj.bound_box]
lower = Vector([min(point[axis] for point in points) for axis in range(3)])
upper = Vector([max(point[axis] for point in points) for axis in range(3)])
center = (lower + upper) / 2
radius = max(upper - lower)
material = bpy.data.materials.new('DiagnosticClay')
material.use_nodes = True
shader = material.node_tree.nodes.get('Principled BSDF')
shader.inputs['Base Color'].default_value = (0.55, 0.55, 0.55, 1)
shader.inputs['Roughness'].default_value = 0.8
for obj in objects:
    diagnostic = bmesh.new()
    diagnostic.from_mesh(obj.data)
    inverse = obj.matrix_world.inverted()
    bmesh.ops.bisect_plane(
        diagnostic,
        geom=list(diagnostic.verts) + list(diagnostic.edges) + list(diagnostic.faces),
        plane_co=inverse @ center,
        plane_no=inverse.to_3x3() @ Vector((0, -1, 0)),
        clear_outer=True,
        clear_inner=False,
    )
    diagnostic.to_mesh(obj.data)
    diagnostic.free()
    obj.data.materials.clear()
    obj.data.materials.append(material)
    for face in obj.data.polygons:
        face.material_index = 0
camera_data = bpy.data.cameras.new('CutawayCamera')
camera = bpy.data.objects.new('CutawayCamera', camera_data)
scene.collection.objects.link(camera)
camera.location = center + Vector((0.7, -3, 1.2)) * radius
camera.rotation_euler = (center - camera.location).to_track_quat('-Z', 'Y').to_euler()
camera_data.type = 'ORTHO'
camera_data.ortho_scale = radius * 1.6
scene.camera = camera
scene.world = bpy.data.worlds.new('CutawayWorld')
scene.world.use_nodes = True
scene.world.node_tree.nodes.get('Background').inputs['Strength'].default_value = 0.8
for offset in [(1, -3, 3), (-2, -2, 2)]:
    data = bpy.data.lights.new('CutawayLight', 'AREA')
    data.energy = 400 * radius * radius
    data.size = 3 * radius
    light = bpy.data.objects.new('CutawayLight', data)
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
scene.render.filepath = str(args.output)
bpy.ops.render.render(write_still=True)
# No source or blend saved: the half-mesh is only a disposable diagnostic view.
