import sys,json,math
from pathlib import Path
import bpy,bmesh,numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
root=Path('D:/Projetos/3dGeneratorNew');sys.path.insert(0,str(root/'scripts'))
import blender_asset_worker as worker
inputs=json.loads((root/'local_data/studio/front-diagnosis-inputs.json').read_text())
out=root/'outputs/remesh-diagnosis/front'

def from_obj(path):
 positions=[];faces=[];repeated=0
 for line in Path(path).read_text().splitlines():
  fields=line.split()
  if fields and fields[0]=='v': positions.append(tuple(map(float,fields[1:4])))
  elif fields and fields[0]=='f':
   face=[int(field.split('/')[0])-1 for field in fields[1:]]
   if len(set(face))!=len(face): repeated+=1
   faces.append(face)
 mesh=bpy.data.meshes.new('diagnostic');mesh.from_pydata(positions,[],faces);mesh.update()
 obj=bpy.data.objects.new(Path(path).stem,mesh);bpy.context.collection.objects.link(obj)
 return obj,repeated

def metrics(obj):
 bm=bmesh.new();bm.from_mesh(obj.data)
 bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7)
 lengths=[edge.calc_length() for edge in bm.edges if edge.is_boundary]
 stats={'boundary_edges':len(lengths),'boundary_length':sum(lengths),'non_manifold_edges':sum(not e.is_manifold for e in bm.edges)}
 bm.free()
 m=obj.data;m.calc_loop_triangles();positions=np.array([obj.matrix_world@v.co for v in m.vertices]);indices=np.array([t.vertices[:] for t in m.loop_triangles]);tri=positions[indices]
 areas=np.linalg.norm(np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]),axis=1)*.5
 stats['triangles']=len(indices);stats['area']=float(areas.sum())
 tree=BVHTree.FromPolygons([Vector(v) for v in positions],indices.tolist(),all_triangles=True)
 rng=np.random.default_rng(0);chosen=rng.choice(len(tri),2000,p=areas/areas.sum());u=rng.random((2000,1));v=rng.random((2000,1));sq=np.sqrt(u);samples=(1-sq)*tri[chosen,0]+sq*(1-v)*tri[chosen,1]+sq*v*tri[chosen,2]
 return stats,tree,samples

source=worker.import_source(Path(inputs['source_glb']));prepared,_=worker.prepare_copy(source,out)
base,base_tree,base_samples=metrics(prepared);results={'source':base,'cases':[]}
for path in [*inputs['old_low'],*inputs['candidates']]:
 if Path(path).suffix=='.glb':
  obj=worker.import_source(Path(path));repeated=None
 else:
  bpy.ops.wm.read_factory_settings(use_empty=True);obj,repeated=from_obj(path)
 stats,tree,samples=metrics(obj)
 for key,points,target in [('source_to_candidate',base_samples,tree),('candidate_to_source',samples,base_tree)]:
  distances=np.array([target.find_nearest(Vector(point))[3] for point in points]);stats[key]={'p95':float(np.quantile(distances,.95)),'max':float(distances.max())}
 stats['file']=path;stats['repeated_index_polygons']=repeated;results['cases'].append(stats)
 print(json.dumps(stats),flush=True)
(out/'geometry-diagnosis.json').write_text(json.dumps(results,indent=2))
# Same opaque clay material for both source and candidate, independent of UV/bake.
source=worker.import_source(Path(inputs['source_glb']));low,_=from_obj(out/'tri-pure.obj')
mat=bpy.data.materials.new('Opaque diagnostic clay');mat.use_nodes=True;mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.6,.6,.6,1)
for obj in (source,low):obj.data.materials.clear();obj.data.materials.append(mat)
worker.render_comparison(source,low,out)
print('SOURCE',json.dumps(base),flush=True)
