import json
import os
from pathlib import Path
from gradio_client import Client, handle_file

root = Path(r'D:/Projetos/3dGeneratorNew')
os.environ['TEMP'] = str(root / 'runtime/temp')
os.environ['TMP'] = os.environ['TEMP']
client = Client(
    'http://127.0.0.1:8080',
    httpx_kwargs={'trust_env': False},
    download_files=str(root / 'logs/ui-client-files'),
)
output = client.predict(
    handle_file(str(root / 'inputs/architecture-gate.webp')),
    api_name='/preprocess_image_1',
)
report = {'endpoint': '/preprocess_image_1', 'input': 'inputs/architecture-gate.webp', 'output': output}
(root / 'logs/ui-preprocess-report.json').write_text(json.dumps(report, indent=2, default=str), encoding='utf-8')
print(json.dumps(report, indent=2, default=str))
