$ErrorActionPreference = 'Stop'
$taskRoot = $PSScriptRoot
$taskCode = Join-Path $taskRoot 'runtime\official\code'
$env:HF_HOME = Join-Path $taskCode 'models'
$env:GRADIO_TEMP_DIR = Join-Path $taskRoot 'runtime\temp\gradio'
$env:TEMP = Join-Path $taskRoot 'runtime\temp'
$env:TMP = $env:TEMP
$env:PYTHONNOUSERSITE = '1'
$env:SETUPTOOLS_USE_DISTUTILS = 'stdlib'
$env:TORCH_HOME = Join-Path $taskRoot 'runtime\cache\torch'
$env:TRITON_CACHE_DIR = Join-Path $taskRoot 'runtime\cache\triton'
$env:CUDA_CACHE_PATH = Join-Path $taskRoot 'runtime\cache\cuda'
$env:SPARSE_DEBUG = '0'
Set-Location $taskCode
& '.\venv\Scripts\python.exe' -u app.py --host 127.0.0.1 --port 8080
