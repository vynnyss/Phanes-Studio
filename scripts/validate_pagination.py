from pathlib import Path
import ast,json,sqlite3,hashlib,requests
from PIL import Image
from gradio_client import Client
import gradio as gr
from studio_service import Studio,ROOT,DATA,connect

base='http://127.0.0.1:8080'
previous=json.loads((DATA/'pagination-restart.json').read_text())
assert requests.get(base+'/api/models').json()==previous['models']
studio=Studio()
initial=studio.reference_images()
assert len(initial)>=4
fixtures=[]
try:
    # Temporary records let us test image page 2 without leaving invented references.
    for index,color in enumerate(((231,17,37),(19,203,83))):
        path=DATA/f'pagination-fixture-{index}.png'
        Image.new('RGB',(17,19),color).save(path)
        digest=hashlib.sha256(path.read_bytes()).hexdigest()
        assert digest not in {row['id'] for row in initial}
        identifier=studio.remember_image(path,name=f'Teste temporário {index}')
        stored=studio.reference_image(identifier)
        assert Path(stored['path']).read_bytes()==path.read_bytes()
        path.unlink()
        assert requests.get(base+'/api/images/'+identifier+'/file').content==Path(stored['path']).read_bytes()
        fixtures.append(stored)
    client=Client(base,verbose=False)
    first=client.predict(api_name='/refresh')
    assert len(first[0])==4 and 'Página 1 de' in first[1]
    assert len(first[2])==4 and 'Página 1 de 2' in first[3]
    second=client.predict(api_name='/models_next_page')
    assert len(second[0])==min(4,len(requests.get(base+'/api/history').json())-4) and 'Página 2 de' in second[1]
    assert {item['caption'] for item in first[0]}.isdisjoint({item['caption'] for item in second[0]})
    # Model and image page states remain independent.
    refreshed=client.predict(api_name='/refresh')
    assert 'Página 2 de' in refreshed[1] and 'Página 1 de 2' in refreshed[3]
    images_second=client.predict(api_name='/images_next_page')
    assert len(images_second[0])==len(initial)+len(fixtures)-4 and 'Página 2 de' in images_second[1]
    refreshed=client.predict(api_name='/refresh')
    assert 'Página 2 de' in refreshed[1] and 'Página 2 de' in refreshed[3]
    last=client.predict(api_name='/refresh')
    assert 'Página 2 de' in last[1]
    back=client.predict(api_name='/models_previous_page')
    assert len(back[0])==4 and 'Página 1 de 2' in back[1]
    source=ast.parse((ROOT/'scripts/studio_app.py').read_text(encoding='utf-8'))
    functions=[]
    for node in source.body:
        if isinstance(node,ast.With):
            break
        if isinstance(node,ast.FunctionDef):
            functions.append(node)
    import html
    from studio_progress import read_progress,stage_label
    namespace={'studio':studio,'gr':gr,'ROOT':ROOT,'Path':Path,'json':json,'PAGE_SIZE':4,
               'html':html,'read_progress':read_progress,'stage_label':stage_label}
    exec(compile(ast.Module(body=functions,type_ignores=[]),'studio_callbacks','exec'),namespace)
    image_view=namespace['image_page_view'](2)
    loaded,notice,*_=namespace['choose_image'](image_view[1],gr.SelectData(None,{'index':0,'selected':True,'value':None}))
    assert loaded==[studio.reference_image(image_view[1][0])['path']]
    assert 'Adicionar imagens à fila' in notice
    model_view=namespace['model_page_view'](2)
    selected=namespace['choose_gallery'](model_view[1],gr.SelectData(None,{'index':1,'selected':True,'value':None}))
    assert selected[0]==model_view[1][1]
    assert selected[1]['value']==studio.variant(selected[0])['model']
    assert gr.Model3D().postprocess(selected[1]['value']).path==selected[1]['value']
    assert namespace['paginate']([],999)==([],1,1)
    evidence={
        'models_count':len(previous['models']), 'references_count':len(initial),
        'page_size':4,'model_pages_and_selection':True,'image_pages_and_reuse':True,
        'independent_page_states':True,'refresh_preserves_pages':True,
        'permanent_copies_and_exact_download':True,'duplicates_by_sha256':True,
        'browser_visual_validation':False,
    }
    # Repeat the same image and verify it creates no extra record.
    duplicate=studio.remember_image(initial[0]['path'],name=initial[0]['name'],used_at=initial[0]['last_used'])
    assert duplicate==initial[0]['id'] and len(studio.reference_images())==len(initial)+len(fixtures)
    (DATA/'pagination-validation.json').write_text(json.dumps(evidence,indent=2),encoding='utf-8')
    print('PASS: paginação real dos dois históricos, estados independentes, seleção, reutilização e download exato')
finally:
    for row in fixtures:
        with connect() as db:
            db.execute('DELETE FROM reference_images WHERE id=?',(row['id'],))
        Path(row['path']).unlink(missing_ok=True)
    requests.post(base+'/api/queue/'+('pause' if previous['paused'] else 'resume')).raise_for_status()
print('Referências temporárias removidas; estado original da fila restaurado')
