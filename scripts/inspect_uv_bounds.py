import sys
from pathlib import Path
import bpy
import numpy as np
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'scripts'))
from blender_asset_worker import create_uv
bpy.ops.wm.open_mainfile(filepath=str(root/'outputs/remesh-comparison/front-20261004/meshopt-update-4000-probe/remesh.blend'))
low=bpy.data.objects['Remesh_low']
create_uv(low,1024,2)
uv=np.array([corner.uv[:] for corner in low.data.uv_layers.active.data])
print('UV BOUNDS',uv.min(axis=0),uv.max(axis=0),flush=True)
