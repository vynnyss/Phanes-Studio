from pathlib import Path
import ast,json,time,shutil,uuid
import gradio as gr
import studio_service as service
from studio_progress import read_progress,stage_label

project=service.ROOT
workspace=project/'local_data/processing-validation'/('run-'+uuid.uuid4().hex)
workspace.mkdir(parents=True,exist_ok=True)
(workspace/'outputs').mkdir(exist_ok=True)
(workspace/'inputs').mkdir(exist_ok=True)
service.ROOT=workspace
service.DATA=workspace/'local_data/studio'
service.DB=service.DATA/'studio.db'
fixture=workspace/'fixture_worker.py'
fixture.write_text('''import sys,time,json,shutil
from pathlib import Path
out=Path(sys.argv[1]);mode=sys.argv[2]
(out/'progress.json').write_text(json.dumps({'stage':'preprocess'}))
time.sleep(1.5)
(out/'progress.json').write_text(json.dumps({'stage':'export'}))
time.sleep(1.5)
if mode=='failure':
 (out/'report.json').write_text(json.dumps({'result':'failed','error':'Controlled validation failure'}))
 sys.exit(1)
shutil.copyfile(sys.argv[3],out/'model.glb')
(out/'report.json').write_text(json.dumps({'result':'completed','validation_fixture':True}))
''',encoding='utf-8')
source=project/'outputs/weapon-pistol-1024/model.glb'
class TestStudio(service.Studio):
    def command(self,job):
        mode='failure' if job['parameters']['seed']==1 else 'success'
        return [str(service.PYTHON),str(fixture),job['output'],mode,str(source)]

studio=TestStudio()
studio.import_reference_images()
studio.pause(True)
studio.start()
module=ast.parse((project/'scripts/studio_app.py').read_text(encoding='utf-8'))
functions=[]
for node in module.body:
    if isinstance(node,ast.With):
        break
    if isinstance(node,ast.FunctionDef):
        functions.append(node)
import html
namespace={'studio':studio,'ROOT':project,'Path':Path,'json':json,'gr':gr,'html':html,
           'PAGE_SIZE':4,'read_progress':read_progress,'stage_label':stage_label}
exec(compile(ast.Module(body=functions,type_ignores=[]),'studio_callbacks','exec'),namespace)
def await_state(identifier,wanted,timeout=15):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        job=studio.job(identifier)
        if job['status']==wanted:
            return job
        if job['status'] in ('failed','completed') and wanted=='running':
            raise AssertionError(job)
        time.sleep(.05)
    raise AssertionError(studio.job(identifier))
try:
    image=project/'inputs/chair.png'
    first=studio.enqueue_generate(image,resolution=512,seed=0,name='Validation fixture')
    assert not studio.history_entries() # Pending does not reserve a model card.
    studio.pause(False)
    await_state(first,'running')
    entry=studio.history_entry(first)
    assert entry['model'] is None and entry['status']=='running'
    selection=namespace['choose_gallery']([first],gr.SelectData(None,{'index':0,'selected':True,'value':None}))
    assert selection[0]==first and selection[1]['visible'] is False
    assert selection[2]['visible'] is False and selection[5]['visible'] is True
    assert 'studio-spinner' in selection[5]['value']
    assert selection[7]['interactive'] is False
    revision=selection[6]
    refs=studio.running_references();assert refs
    reference_id=next(iter(refs))
    image_selection=namespace['choose_image']([reference_id],gr.SelectData(None,{'index':0,'selected':True,'value':None}))
    assert image_selection[2]==first
    await_state(first,'completed')
    assert studio.history_entry(first)['status']=='completed'
    completed=namespace['selected_refresh'](first,revision)
    assert completed[0]['value']==str(Path(studio.job(first)['output'])/'model.glb')
    assert completed[0]['visible'] is True and completed[1]['visible'] is True
    assert completed[4]['visible'] is False and completed[6]['interactive'] is True
    assert all(value.get('__type__')=='update' for value in namespace['selected_refresh'](first,completed[5]))
    failed=studio.enqueue_generate(image,resolution=512,seed=1,name='Failure fixture')
    await_state(failed,'failed')
    failure=namespace['selected_model'](failed)
    assert 'Controlled validation failure' in failure[4]['value']
    assert '<div class="studio-spinner"' not in failure[4]['value']
    assert failure[0]['visible'] is False
    # Another active job must not replace a completed selected model.
    other=studio.enqueue_generate(image,resolution=512,seed=0,name='Other fixture')
    await_state(other,'running')
    refreshed=namespace['refresh']([],1,[],1,first,completed[5],None)
    assert all(value.get('__type__')=='update' for value in refreshed[-7:])
    await_state(other,'completed')
    log_dir=workspace/'progress_parser';log_dir.mkdir(exist_ok=True)
    (log_dir/'resources.csv').write_text('0,generate_and_preview,1,1,1,1,1,1\n')
    (log_dir/'worker.log').write_text('Sampling shape SLat (HR): 50%|#####| 7/14 [01:00<01:00]\n')
    parsed=read_progress(log_dir);assert parsed['iteration']==7 and parsed['total']==14
    (log_dir/'progress.json').write_text(json.dumps({'stage':'export'}))
    parsed=read_progress(log_dir);assert parsed['stage']=='export' and parsed['iteration'] is None
    evidence={'isolated_control_flow_fixture':True,'pending_hidden_running_card':True,
        'processing_image_selects_job':True,'spinner_and_actions_disabled':True,
        'same_id_completed_auto_glb':True,'failure_visible_no_fake_model':True,
        'other_jobs_do_not_replace_selection':True,'real_stage_parser':True,
        'browser_visual_validation':False}
    (project/'local_data/studio/processing-validation.json').write_text(json.dumps(evidence,indent=2),encoding='utf-8')
    print('PASS: cartões ao iniciar, imagem ligada ao job, carregamento, GLB automático, falha e seleção preservada')
finally:
    studio.close()
