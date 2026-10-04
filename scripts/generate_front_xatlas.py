"""Create xatlas UVs with explicit correspondence to approved triangle corners."""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime/tools/xatlas-python"))
import xatlas

parser = argparse.ArgumentParser()
parser.add_argument("--output", type=Path, default=ROOT / "outputs/uv-xatlas/front")
parser.add_argument("--padding", type=int, default=4)
parser.add_argument("--brute-force", action="store_true")
args = parser.parse_args()
OUTPUT = args.output
mesh = np.load(OUTPUT / "approved-geometry.npz")
positions = mesh["positions"]
faces = mesh["faces"]
atlas = xatlas.Atlas()
# Scale only the parameterization input to avoid numeric rejection of tiny faces.
# Approved geometry is untouched; only UV corner coordinates are transferred back.
atlas.add_mesh(positions * 1000, faces)
options = xatlas.PackOptions()
options.resolution = 1024
options.padding = args.padding
options.bruteForce = args.brute_force
options.bilinear = True
options.rotate_charts = True
options.create_image = True
started = time.perf_counter()
atlas.generate(pack_options=options)
vmapping, indices, uvs = atlas[0]
assert atlas.atlas_count == 1, "Expected one atlas"
assert np.array_equal(vmapping[indices], faces), "xatlas changed face order or correspondence"
assert np.isfinite(uvs).all()
np.savez(OUTPUT / "atlas.npz", faces=faces, corner_uv=uvs[indices])
report = {
    "version": importlib.metadata.version("xatlas"),
    "parameterization_input_scale": 1000,
    "generate_s": time.perf_counter() - started,
    "width": atlas.width,
    "height": atlas.height,
    "atlas_count": atlas.atlas_count,
    "charts": atlas.get_mesh_chart_count(0),
    "native_utilization": atlas.utilization,
    "resolution_requested": 1024,
    "padding_native_pixels": args.padding,
    "brute_force": args.brute_force,
    "input_vertices": len(positions),
    "atlas_vertices": len(vmapping),
    "triangles": len(faces),
    "corner_correspondence_exact": True,
}
(OUTPUT / "atlas-report.json").write_text(json.dumps(report, indent=2))
from PIL import Image
Image.fromarray(atlas.chart_image).save(OUTPUT / "atlas-charts.png")
print(json.dumps(report), flush=True)
