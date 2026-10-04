import bpy,numpy as np
bpy.ops.wm.open_mainfile(filepath='D:/Projetos/3dGeneratorNew/outputs/remesh-tests/pistol-instant-final-12000/optimized.blend')
o=bpy.data.objects['Remesh_low']; m=o.data;m.calc_loop_triangles(); uv=m.uv_layers.active.data
areas=[]
for t in m.loop_triangles:
 a=np.array([uv[i].uv[:] for i in t.loops]); areas.append(abs(np.cross(a[1]-a[0],a[2]-a[0]))*.5)
print('UV AREA',sum(areas),min(areas),max(areas));print('FIRST UV',[[uv[i].uv[:] for i in t.loops] for t in list(m.loop_triangles)[:5]])
bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
print('SMART',bpy.ops.uv.smart_project(angle_limit=1.15,island_margin=.002));print('PACK',bpy.ops.uv.pack_islands(udim_source='ORIGINAL_AABB',rotate=True,scale=True,margin_method='SCALED',margin=.002));bpy.ops.object.mode_set(mode='OBJECT')
a=np.array([x.uv[:] for x in o.data.uv_layers.active.data]); print('NEW UV',a.min(axis=0),a.max(axis=0))
