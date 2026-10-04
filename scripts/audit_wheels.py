from pathlib import Path
import json
import zipfile

root = Path(r'D:/Projetos/3dGeneratorNew')
rows = []
for wheel in (root / 'runtime/official/code/whl').glob('*.whl'):
    with zipfile.ZipFile(wheel) as archive:
        metadata_name = next(name for name in archive.namelist() if name.endswith('.dist-info/METADATA'))
        metadata = archive.read(metadata_name).decode('utf-8', errors='replace')
        license_names = [name for name in archive.namelist() if 'license' in name.lower() or 'copying' in name.lower()]
        rows.append({
            'wheel': wheel.name,
            'metadata': metadata,
            'licenses': {name: archive.read(name).decode('utf-8', errors='replace') for name in license_names},
        })
(root / 'logs/wheel-audit.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')
for row in rows:
    print(row['wheel'], list(row['licenses']))
