from pathlib import Path
import json
import bpy

root = Path(r'D:/Projetos/3dGeneratorNew')
folder = root / 'outputs/prop-bottle-1024-default/blender'
bpy.ops.wm.open_mainfile(filepath=str(folder / 'inspection.blend'))
changed = []
for material in bpy.data.materials:
    if not material.node_tree:
        continue
    nodes = material.node_tree.nodes
    shader = next((node for node in nodes if node.type == 'BSDF_PRINCIPLED'), None)
    if shader is None:
        continue
    color = shader.inputs.get('Base Color')
    if not color or not color.is_linked:
        continue
    texture = color.links[0].from_node
    alpha = texture.outputs.get('Alpha')
    if alpha is None:
        continue
    material.node_tree.links.new(alpha, shader.inputs['Alpha'])
    changed.append(material.name)
scene = bpy.context.scene
scene.render.filepath = str(folder / 'alpha-enabled.png')
bpy.ops.wm.save_as_mainfile(filepath=str(folder / 'alpha-enabled.blend'))
bpy.ops.render.render(write_still=True)
(folder / 'alpha-enabled-report.json').write_text(json.dumps({
    'materials_changed': changed,
    'change': 'Texture Alpha connected to Principled Alpha, as README instructs; geometry and UV unchanged',
    'original_glb_modified': False,
}), encoding='utf-8')
