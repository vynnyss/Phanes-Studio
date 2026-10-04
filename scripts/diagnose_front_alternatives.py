import bpy,bmesh,sys,json,subprocess,ast
from pathlib import Path
root=Path('D:/Projetos/3dGeneratorNew');sys.path.insert(0,str(root/'scripts'))
import blender_asset_worker as worker
source=root/'outputs/studio/d22cab3db100452a8d7de59d84debfc9/model.glb';out=root/'outputs/remesh-diagnosis/front';exe=root/'runtime/tools/instant-meshes/bin/Instant Meshes.exe'
# Reuse exactly the diagnostic metrics, independently of materials.
module=ast.parse((root/'scripts/diagnose_front_geometry.py').read_text(encoding='utf-8'));funcs=[x for x in module.body if isinstance(x,ast.FunctionDef)]
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
exec(compile(ast.Module(body=funcs,type_ignores=[]),'geometry_metrics','exec'))
base_obj=worker.import_source(source);low,_=worker.prepare_copy(base_obj,out)
base,tree,points=metrics(low)
results=[]
for mode in ('decimate-welded','decimate-raw','voxel-instant'):
 high=worker.import_source(source)
 low,_=worker.prepare_copy(high,out) if mode!='decimate-raw' else (high,None)
 if mode.startswith('decimate'):
  worker.select_only(low);m=low.modifiers.new('diagnostic','DECIMATE');m.ratio=12000/249721;m.use_collapse_triangulate=True;bpy.ops.object.modifier_apply(modifier=m.name)
  worker.write_obj(low,out/(mode+'.obj'))
 else:
  worker.select_only(low);low.data.remesh_voxel_size=max(low.dimensions)/300;bpy.ops.object.voxel_remesh();worker.write_obj(low,out/'voxel-source.obj')
  with (out/'voxel-instant.log').open('w') as log:
   subprocess.run([str(exe),str(out/'voxel-source.obj'),'-o',str(out/(mode+'.obj')),'-r','6','-p','6','-f','12000','-c','45','-d','-t','6'],stdout=log,stderr=subprocess.STDOUT,timeout=120)
  low,_=from_obj(out/(mode+'.obj'))
 stats,target,samples=metrics(low)
 distances=np.array([target.find_nearest(Vector(p))[3] for p in points]);stats['source_to_candidate_p95']=float(np.quantile(distances,.95));stats['source_to_candidate_max']=float(distances.max());stats['mode']=mode;results.append(stats);print(json.dumps(stats),flush=True)
(out/'alternative-diagnosis.json').write_text(json.dumps({'source':base,'cases':results},indent=2))
high=worker.import_source(source);low,_=from_obj(out/'decimate-welded.obj')
mat=bpy.data.materials.new('Opaque clay');mat.use_nodes=True;mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.6,.6,.6,1)
for obj in (high,low):obj.data.materials.clear();obj.data.materials.append(mat)
clay=out/'decimate-clay';clay.mkdir(exist_ok=True);worker.render_comparison(high,low,clay)
