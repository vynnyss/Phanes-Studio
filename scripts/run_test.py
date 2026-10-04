import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / 'runtime' / 'official' / 'code'
os.environ['HF_HOME'] = str(CODE / 'models')
os.environ['GRADIO_TEMP_DIR'] = str(ROOT / 'runtime' / 'temp' / 'gradio')
os.environ['TEMP'] = str(ROOT / 'runtime' / 'temp')
os.environ['TMP'] = os.environ['TEMP']
os.environ['PYTHONNOUSERSITE'] = '1'
os.environ['SETUPTOOLS_USE_DISTUTILS'] = 'stdlib'
os.environ['TORCH_HOME'] = str(ROOT / 'runtime' / 'cache' / 'torch')
os.environ['TRITON_CACHE_DIR'] = str(ROOT / 'runtime' / 'cache' / 'triton')
os.environ['CUDA_CACHE_PATH'] = str(ROOT / 'runtime' / 'cache' / 'cuda')
INITIAL_DIRECTORY = Path.cwd()
os.chdir(CODE)
sys.path.insert(0, str(CODE))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--resolution', choices=['512', '1024'], default='512')
    parser.add_argument('--name', required=True)
    parser.add_argument('--faces', type=int, default=250000)
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--texture', type=int, choices=[512, 1024, 2048], default=2048)
    args = parser.parse_args()
    if not args.input.is_absolute():
        args.input = (INITIAL_DIRECTORY / args.input).resolve()

    import psutil
    from PIL import Image
    from pipeline_worker import PipelineWorker

    output = ROOT / 'outputs' / args.name
    output.mkdir(parents=True, exist_ok=True)
    stop = threading.Event()
    stage = ['loading']
    samples = []
    process = psutil.Process()

    def monitor():
        with (output / 'resources.csv').open('w', newline='', encoding='utf-8') as stream:
            writer = csv.DictWriter(stream, fieldnames=[
                'time_s', 'stage', 'tree_rss_bytes', 'tree_private_bytes', 'system_used_bytes',
                'system_available_bytes', 'gpu_global_mib', 'gpu_util_percent',
            ])
            writer.writeheader()
            while not stop.is_set():
                rss = 0
                private = 0
                for item in [process] + process.children(recursive=True):
                    try:
                        process_memory = item.memory_info()
                        rss += process_memory.rss
                        private += getattr(process_memory, 'private', 0)
                    except psutil.Error:
                        pass
                memory = psutil.virtual_memory()
                gpu_memory = None
                gpu_util = None
                try:
                    result = subprocess.run([
                        'nvidia-smi', '--query-gpu=memory.used,utilization.gpu',
                        '--format=csv,noheader,nounits',
                    ], capture_output=True, text=True, timeout=10)
                    values = result.stdout.strip().split(',')
                    gpu_memory, gpu_util = [float(value.strip()) for value in values]
                except Exception:
                    pass
                sample = {
                    'time_s': round(time.perf_counter() - started, 3),
                    'stage': stage[0],
                    'tree_rss_bytes': rss,
                    'tree_private_bytes': private,
                    'system_used_bytes': memory.used,
                    'system_available_bytes': memory.available,
                    'gpu_global_mib': gpu_memory,
                    'gpu_util_percent': gpu_util,
                }
                samples.append(sample)
                writer.writerow(sample)
                stream.flush()
                stop.wait(1)

    started = time.perf_counter()
    sampler = threading.Thread(target=monitor, daemon=True)
    sampler.start()
    report = {
        'input': str(args.input.resolve()),
        'input_sha256': hashlib.sha256(args.input.read_bytes()).hexdigest(),
        'seed': args.seed,
        'requested_resolution': int(args.resolution),
        'pipeline_type': '512' if args.resolution == '512' else '1024_cascade',
        'low_vram': 'official default True',
        'parameters': {
            'ss': dict(steps=14, guidance_strength=7.5, guidance_rescale=0.7, rescale_t=5.0),
            'shape': dict(steps=14, guidance_strength=7.5, guidance_rescale=0.5, rescale_t=3.0),
            'texture': dict(steps=14, guidance_strength=1.0, guidance_rescale=0.0, rescale_t=3.0),
            'decimation_target': args.faces,
            'texture_size': args.texture,
            'preview_views': 4,
        },
        'result': 'running',
        'vertices': None,
        'triangles': None,
        'gpu_process_peak': None,
        'gpu_process_peak_reason': 'WDDM global sampling; not attributable to worker',
    }
    (output / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    worker = None
    try:
        worker = PipelineWorker()
        stage[0] = 'preprocess'
        image = worker.preprocess(Image.open(args.input))
        image.save(output / 'preprocessed.png')
        stage[0] = 'generate_and_preview'
        generation_start = time.perf_counter()
        state, images = worker.generate(
            image=image,
            seed=args.seed,
            ss_params=report['parameters']['ss'],
            shape_params=report['parameters']['shape'],
            tex_params=report['parameters']['texture'],
            pipeline_type=report['pipeline_type'],
            nviews=4,
            profiling=dict(
                enable_python=False, enable_torch=False, enable_sync_hunter=False,
                delay_sec=0, max_duration_sec=0, max_events=100000,
            ),
        )
        report['generation_and_preview_s'] = time.perf_counter() - generation_start
        report['actual_resolution'] = state['res']
        import numpy as np
        np.savez_compressed(output / 'latents.npz', **state)
        for key, frames in images.items():
            for index, frame in enumerate(frames):
                Image.fromarray(np.asarray(frame).astype('uint8')).save(output / f'{key}_{index}.png')
        stage[0] = 'export'
        export_start = time.perf_counter()
        glb_path = output / 'model.glb'
        worker.extract_glb(state, args.faces, args.texture, str(glb_path))
        report['export_s'] = time.perf_counter() - export_start
        report['output_bytes'] = glb_path.stat().st_size
        report['output_sha256'] = hashlib.sha256(glb_path.read_bytes()).hexdigest()
        import trimesh
        scene = trimesh.load(glb_path, force='scene', process=False)
        report['vertices'] = sum(len(mesh.vertices) for mesh in scene.geometry.values())
        report['triangles'] = sum(len(mesh.faces) for mesh in scene.geometry.values())
        report['result'] = 'completed'
        report['cuda_oom'] = False
    except Exception as error:
        report['result'] = 'failed'
        report['failed_stage'] = stage[0]
        report['error'] = str(error)
        report['cuda_oom'] = 'out of memory' in str(error).lower()
        traceback.print_exc()
    finally:
        stage[0] = 'shutdown'
        if worker is not None:
            worker.shutdown()
            if worker.process.is_alive():
                worker.process.terminate()
                worker.process.join(timeout=10)
        stop.set()
        sampler.join(timeout=15)
        report['total_s'] = time.perf_counter() - started
        report['peak_tree_rss_bytes'] = max((s['tree_rss_bytes'] for s in samples), default=None)
        report['peak_tree_private_bytes'] = max((s['tree_private_bytes'] for s in samples), default=None)
        valid_gpu = [s['gpu_global_mib'] for s in samples if s['gpu_global_mib'] is not None]
        report['peak_gpu_global_mib'] = max(valid_gpu, default=None)
        report['stage_peaks'] = {}
        for name in sorted({s['stage'] for s in samples}):
            rows = [s for s in samples if s['stage'] == name]
            gpu = [s['gpu_global_mib'] for s in rows if s['gpu_global_mib'] is not None]
            report['stage_peaks'][name] = {
                'tree_rss_bytes': max(s['tree_rss_bytes'] for s in rows),
                'tree_private_bytes': max(s['tree_private_bytes'] for s in rows),
                'gpu_global_mib': max(gpu, default=None),
                'min_system_available_bytes': min(s['system_available_bytes'] for s in rows),
            }
        (output / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    if report['result'] != 'completed':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
