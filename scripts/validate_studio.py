import requests,json,uuid
from pathlib import Path
base='http://127.0.0.1:8080'; session='history-validation-local'
from gradio_client import Client
client=Client(base,verbose=False)
loaded=client.predict(api_name='/refresh')
assert len(loaded[0])>=1
# Exercise the actual selection callback against persisted history, without
# launching a second executor. Visual browser inspection is separately pending.
import ast,gradio as gr
from studio_service import Studio,ROOT
source=ast.parse((ROOT/'scripts/studio_app.py').read_text(encoding='utf-8'))
selected=[]
for node in source.body:
    if isinstance(node,ast.With):
        break
    if isinstance(node,ast.FunctionDef):
        selected.append(node)
import html
from studio_progress import read_progress,stage_label
namespace={'studio':Studio(),'Path':Path,'json':json,'gr':gr,'html':html,'ROOT':ROOT,
           'PAGE_SIZE':4,'read_progress':read_progress,'stage_label':stage_label}
exec(compile(ast.Module(body=selected,type_ignores=[]),'studio_callbacks','exec'),namespace)
identifiers=[model['id'] for model in namespace['studio'].variants()]
event=gr.SelectData(None,{'index':0,'value':None,'selected':True})
result=namespace['choose_gallery'](identifiers,event)
assert result[0]==identifiers[0] and Path(result[1]['value']).is_file() and result[1]['value']==result[2]['value']
assert gr.Model3D().postprocess(result[1]['value']).path==result[1]['value']
print('Gallery refresh and actual selection callback passed')
models=requests.get(base+'/api/models').json();low=next(m for m in models if m['kind']=='low');high=next(m for m in models if m['id']==low['parent_id'])
assert high['kind']=='high' and low['asset_id']==high['asset_id']
for m in (high,low):
 result=requests.get(base+'/api/models/'+m['id']+'/glb'); assert result.content==Path(m['model']).read_bytes()
print('High/low originals, lineage and GLB downloads verified')
requests.post(base+'/api/queue/pause').raise_for_status()
parent=high['id']; params={'variant_id':parent,'method':'instant','triangles':12000,'texture':1024,'request_key':'pending-validation-cancel-'+uuid.uuid4().hex}
a=requests.post(base+'/api/jobs/remesh',json=params); b=requests.post(base+'/api/jobs/remesh',json=params);assert a.json()['job_id']==b.json()['job_id']
j=a.json()['job_id']; assert requests.get(base+'/api/jobs/'+j).json()['status']=='pending'
assert requests.post(base+'/api/jobs/'+j+'/cancel').status_code==200
assert requests.get(base+'/api/jobs/'+j).json()['status']=='cancelled'
assert requests.post(base+'/api/jobs/remesh',json=dict(params,triangles=8000)).status_code==400
assert requests.post(base+'/api/jobs/remesh',json={'variant_id':parent,'triangles':'wrong'}).status_code==422
jobs=requests.get(base+'/api/jobs').json(); raw=next(x for x in jobs if x['request_key']=='quadriflow-raw-real'); voxel=next(x for x in jobs if x['request_key']=='quadriflow-voxel-real');assert raw['status']=='failed' and voxel['status']=='failed'
assert raw['finished']<=voxel['created'] or raw['finished']<=voxel['finished']
requests.post(base+'/api/queue/resume').raise_for_status()
evidence={'models':models,'jobs':jobs,'lineage_downloads_idempotency_cancel_validation':True,'gallery_callback_events':'actual callback and Gradio Model3D postprocess passed','browser_visual_validation':False}
p=Path('D:/Projetos/3dGeneratorNew/local_data/studio/validation.json');p.write_text(json.dumps(evidence,indent=2),encoding='utf-8')
print('API lifecycle checks passed')
