from pathlib import Path
from PIL import Image, ImageDraw

root = Path(r'D:/Projetos/3dGeneratorNew')
files = sorted((root / 'runtime/official/code/assets/example_image').glob('*.webp'))
canvas = Image.new('RGB', (1200, ((len(files) + 7) // 8) * 170), 'white')
draw = ImageDraw.Draw(canvas)
for index, path in enumerate(files):
    thumb = Image.open(path).convert('RGB')
    thumb.thumbnail((145, 145))
    x = (index % 8) * 150
    y = (index // 8) * 170
    canvas.paste(thumb, (x, y))
    draw.text((x + 4, y + 146), str(index), fill='black')
canvas.save(root / 'logs/examples-contact-sheet.jpg')
(root / 'logs/examples-index.txt').write_text('\n'.join(str(p) for p in files), encoding='utf-8')
