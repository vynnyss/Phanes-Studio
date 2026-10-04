import io
import json
from pathlib import Path
import struct
from PIL import Image

root = Path(r'D:/Projetos/3dGeneratorNew')
path = root / 'outputs/prop-bottle-1024-default/model.glb'
data = path.read_bytes()
json_size, _ = struct.unpack_from('<II', data, 12)
doc = json.loads(data[20:20 + json_size])
base = 20 + json_size + 8
image = doc['images'][0]
view = doc['bufferViews'][image['bufferView']]
start = base + view.get('byteOffset', 0)
texture = Image.open(io.BytesIO(data[start:start + view['byteLength']])).convert('RGBA')
alpha = texture.getchannel('A')
histogram = alpha.histogram()
report = {
    'texture_size': texture.size,
    'alpha_range': alpha.getextrema(),
    'fraction_alpha_below_255': sum(histogram[:-1]) / (texture.width * texture.height),
    'alpha_mode_glb': doc['materials'][0].get('alphaMode', 'OPAQUE'),
    'note': 'Atlas background pixels also count; this is not the fraction of visible glass surface',
}
(root / 'outputs/prop-bottle-1024-default/alpha-report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report, indent=2))
