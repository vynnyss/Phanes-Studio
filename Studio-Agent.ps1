param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$StudioArguments
)

$ErrorActionPreference = 'Stop'
$taskPython = Join-Path $PSScriptRoot 'runtime\official\code\venv\Scripts\python.exe'
$taskClient = Join-Path $PSScriptRoot 'scripts\studio_cli.py'
$env:PYTHONUTF8 = '1'
& $taskPython $taskClient @StudioArguments
exit $LASTEXITCODE
