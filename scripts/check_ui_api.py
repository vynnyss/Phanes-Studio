from pathlib import Path
import json
from gradio_client import Client

root = Path(r'D:/Projetos/3dGeneratorNew')
client = Client('http://127.0.0.1:8080', httpx_kwargs={'trust_env': False})
info = client.view_api(return_format='dict', print_info=False)
(root / 'logs/ui-api.json').write_text(json.dumps(info, indent=2), encoding='utf-8')
print(list(info.get('named_endpoints', {})))
