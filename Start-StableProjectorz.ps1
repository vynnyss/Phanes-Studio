$ErrorActionPreference = 'Stop'
$taskExecutable = Join-Path $PSScriptRoot 'desktop\dist\3DStudio\Phanes Studio.exe'
if (-not (Test-Path -LiteralPath $taskExecutable)) {
    throw 'Executável não encontrado. Consulte docs/DESKTOP_E_AGENTES.md para reconstruir o aplicativo.'
}
Start-Process -FilePath $taskExecutable -WorkingDirectory $PSScriptRoot -WindowStyle Hidden
