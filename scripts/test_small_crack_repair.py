import bpy,bmesh,sys,json,math
from pathlib import Path
root=Path('D:/Projetos/3dGeneratorNew');sys.path.insert(0,str(root/'scripts'));import blender_asset_worker as w
out=root/'outputs/remesh-diagnosis/front';high=w.import_source(root/'outputs/studio/d22cab3db100452a8d7de59d84debfc9/model.glb');low,_=w.prepare_copy(high,out)
bm=bmesh.new();bm.from_mesh(low.data);remaining={e for e in bm.edges if e.is_boundary};filled=0;faces=0;size=max(low.dimensions)
while remaining:
 seed=remaining.pop();component={seed};pending=[seed]
 while pending:
  edge=pending.pop()
  for vertex in edge.verts:
   for adjacent in vertex.link_edges:
    if adjacent in remaining:
     remaining.remove(adjacent);component.add(adjacent);pending.append(adjacent)
 vertices={v for e in component for v in e.verts}
 loop=all(sum(e in component for e in v.link_edges)==2 for v in vertices)
 if loop and len(vertices)<=8 and sum(e.calc_length() for e in component)<=size*.025:
  added=bmesh.ops.holes_fill(bm,edges=list(component),sides=0)['faces'];filled+=bool(added);faces+=len(added)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(low.data);bm.free();low.data.update()
w.select_only(low);m=low.modifiers.new('prepared simplification','DECIMATE');m.ratio=12000/249721;m.use_collapse_triangulate=True;bpy.ops.object.modifier_apply(modifier=m.name)
bm=bmesh.new();bm.from_mesh(low.data);print('RESULT',json.dumps({'small_loops_filled':filled,'faces_added':faces,'boundary_edges':sum(e.is_boundary for e in bm.edges),'boundary_length':sum(e.calc_length() for e in bm.edges if e.is_boundary),'stats':w.mesh_stats(low)}),flush=True);bm.free()
w.write_obj(low,out/'simplify-repaired.obj')
