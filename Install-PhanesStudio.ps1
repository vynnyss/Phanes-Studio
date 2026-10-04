param(
    [switch]$Plan,
    [switch]$CheckOnly,
    [switch]$SkipModels,
    [switch]$OptionalTools,
    [switch]$NoShortcuts,
    [string]$BlenderPath
)

$ErrorActionPreference = 'Stop'
$taskProjectRoot = $PSScriptRoot
$taskSources = Get-Content -Raw -Encoding UTF8 (Join-Path $taskProjectRoot 'setup\sources.json') | ConvertFrom-Json
$taskOfficial = Join-Path $taskProjectRoot 'runtime\official'
$taskCode = Join-Path $taskOfficial 'code'
$taskPython = Join-Path $taskCode 'venv\Scripts\python.exe'

function Invoke-PhanesCommand {
    param([string]$Executable, [string[]]$Arguments)
    & $Executable @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Comando falhou com código ${LASTEXITCODE}: $Executable"
    }
}

function Save-PhanesDownload {
    param([string]$Url, [string]$Destination, [string]$Sha256)
    if (Test-Path -LiteralPath $Destination) {
        $taskExistingHash = (Get-FileHash -LiteralPath $Destination -Algorithm SHA256).Hash
        if ($taskExistingHash -ieq $Sha256) {
            return
        }
        throw "Hash diferente do esperado: $Destination. Preserve/remova esse arquivo antes de repetir."
    }
    [System.IO.Directory]::CreateDirectory((Split-Path -Parent $Destination)) | Out-Null
    $taskPartial = "$Destination.download"
    Write-Host "Baixando $Url"
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    Invoke-WebRequest -Uri $Url -OutFile $taskPartial -UseBasicParsing
    $taskDownloadedHash = (Get-FileHash -LiteralPath $taskPartial -Algorithm SHA256).Hash
    if ($taskDownloadedHash -ine $Sha256) {
        throw "Download rejeitado: SHA256 diferente do esperado para $Url"
    }
    Move-Item -LiteralPath $taskPartial -Destination $Destination
}

function Expand-PhanesArchive {
    param([string]$Archive, [string]$Destination)
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $taskExtractionRoot = [System.IO.Path]::GetFullPath($Destination).TrimEnd('\') + '\'
    $taskArchive = [System.IO.Compression.ZipFile]::OpenRead($Archive)
    try {
        foreach ($taskEntry in $taskArchive.Entries) {
            $taskEntryPath = [System.IO.Path]::GetFullPath((Join-Path $taskExtractionRoot $taskEntry.FullName))
            if (-not $taskEntryPath.StartsWith($taskExtractionRoot, [StringComparison]::OrdinalIgnoreCase)) {
                throw "Caminho fora da pasta de extração: $($taskEntry.FullName)"
            }
            $taskFileType = ($taskEntry.ExternalAttributes -shr 16) -band 0xF000
            if ($taskFileType -eq 0xA000) {
                throw "Link simbólico não permitido no pacote: $($taskEntry.FullName)"
            }
        }
        foreach ($taskEntry in $taskArchive.Entries) {
            $taskEntryPath = [System.IO.Path]::GetFullPath((Join-Path $taskExtractionRoot $taskEntry.FullName))
            if (-not $taskEntry.Name) {
                [System.IO.Directory]::CreateDirectory($taskEntryPath) | Out-Null
                continue
            }
            [System.IO.Directory]::CreateDirectory((Split-Path -Parent $taskEntryPath)) | Out-Null
            [System.IO.Compression.ZipFileExtensions]::ExtractToFile($taskEntry, $taskEntryPath, $false)
        }
    } finally {
        $taskArchive.Dispose()
    }
}

if ($Plan) {
    [pscustomobject]@{
        project = $taskProjectRoot
        runtime = $taskSources.runtime
        models = $taskSources.models
        huggingface = $taskSources.huggingface
        steps = @('Runtime v22/Python 3.11', 'Ambiente Python e dependências CUDA', 'Pesos', 'Correção OpenEXR e pacotes Studio', 'Electron e meshoptimizer', 'Empacotamento e atalhos')
        skipModels = [bool]$SkipModels
        optionalTools = [bool]$OptionalTools
    } | ConvertTo-Json -Depth 5
    return
}

if ($CheckOnly) {
    if (-not (Test-Path -LiteralPath $taskPython)) {
        throw 'Runtime não instalado. Execute Install-PhanesStudio.ps1 primeiro.'
    }
    Invoke-PhanesCommand $taskPython @((Join-Path $taskProjectRoot 'scripts\install_runtime.py'), '--check')
    return
}

if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT -or -not [Environment]::Is64BitOperatingSystem) {
    throw 'O instalador atual suporta Windows x64.'
}
$taskNode = (Get-Command node.exe -ErrorAction Stop).Source
$taskNpm = (Get-Command npm.cmd -ErrorAction Stop).Source
Invoke-PhanesCommand $taskNode @('-e', 'const [major, minor] = process.versions.node.split(String.fromCharCode(46)).map(Number); if (major < 22 || (major === 22 && minor < 12)) process.exit(1);')
if (-not (Get-Command nvidia-smi.exe -ErrorAction SilentlyContinue)) {
    throw 'Instale o driver NVIDIA compatível com CUDA 12.8 antes de instalar o runtime de geração.'
}

if ($BlenderPath) {
    $taskBlender = [System.IO.Path]::GetFullPath($BlenderPath)
    if (-not (Test-Path -LiteralPath $taskBlender -PathType Leaf)) {
        throw "Blender não encontrado: $taskBlender"
    }
} else {
    $taskBlenderCommand = Get-Command blender.exe -ErrorAction SilentlyContinue
    $taskBlender = if ($taskBlenderCommand) { $taskBlenderCommand.Source } else { $null }
    if (-not $taskBlender) {
        $taskBlenderBase = Join-Path $env:ProgramFiles 'Blender Foundation'
        if (Test-Path -LiteralPath $taskBlenderBase) {
            $taskBlender = Get-ChildItem -LiteralPath $taskBlenderBase -Filter blender.exe -Recurse |
                Sort-Object FullName -Descending | Select-Object -First 1 -ExpandProperty FullName
        }
    }
}
if (-not $taskBlender) {
    throw 'Instale Blender 5.2 ou informe -BlenderPath CAMINHO\blender.exe. Blender não é baixado por este instalador.'
}
if (Get-Process -Name 'Phanes Studio' -ErrorAction SilentlyContinue) {
    throw 'Feche a janela Phanes Studio antes de instalar/reconstruir.'
}
if (Test-Path -LiteralPath $taskPython) {
    $taskClientScript = Join-Path $taskProjectRoot 'scripts\studio_cli.py'
    $taskRuntimeStatus = & $taskPython $taskClientScript status
    if ($LASTEXITCODE -eq 0) {
        $taskRuntimeState = $taskRuntimeStatus | ConvertFrom-Json
        if ($taskRuntimeState.running -and ($taskRuntimeState.clients.Count -gt 0 -or $taskRuntimeState.work.running -gt 0 -or $taskRuntimeState.work.pending -gt 0)) {
            throw 'Há clientes ou trabalhos na fila. Conclua os trabalhos e feche os clientes antes de instalar.'
        }
    }
}

$env:PYTHONUTF8 = '1'
$env:PYTHONNOUSERSITE = '1'
$env:PYTHONHOME = $null
$env:PYTHONPATH = $null
$env:SETUPTOOLS_USE_DISTUTILS = 'stdlib'
$env:PIP_CONFIG_FILE = 'NUL'
$env:HF_HOME = Join-Path $taskCode 'models'
$env:TEMP = Join-Path $taskProjectRoot 'runtime\temp'
$env:TMP = $env:TEMP
$env:ELECTRON_CACHE = Join-Path $taskProjectRoot 'runtime\cache\electron'
[System.IO.Directory]::CreateDirectory($env:TEMP) | Out-Null

$taskPortablePython = Join-Path $taskOfficial 'tools\python\python.exe'
$taskUpstreamInstaller = Join-Path $taskCode 'install.py'
if (-not (Test-Path -LiteralPath $taskPortablePython) -or -not (Test-Path -LiteralPath $taskUpstreamInstaller)) {
    if (Test-Path -LiteralPath $taskOfficial) {
        throw 'Runtime parcial encontrado. Preserve essa pasta e mova-a manualmente antes de instalar novamente.'
    }
    $taskZip = Join-Path $taskProjectRoot 'runtime\cache\setup\trellis2-stableprojectorz_v22.zip'
    Save-PhanesDownload $taskSources.runtime.url $taskZip $taskSources.runtime.sha256
    Expand-PhanesArchive $taskZip $taskOfficial
}

if (-not (Test-Path -LiteralPath $taskPython)) {
    & $taskPortablePython -m pip --version
    if ($LASTEXITCODE -ne 0) {
        Invoke-PhanesCommand $taskPortablePython @((Join-Path $taskOfficial 'tools\python\get-pip.py'))
    }
    Invoke-PhanesCommand $taskPortablePython @('-m', 'pip', 'install', 'virtualenv==21.2.0')
    Invoke-PhanesCommand $taskPortablePython @('-m', 'virtualenv', (Join-Path $taskCode 'venv'))
}
$taskPythonArguments = @((Join-Path $taskProjectRoot 'scripts\install_runtime.py'))
if ($SkipModels) { $taskPythonArguments += '--skip-models' }
if ($OptionalTools) { $taskPythonArguments += '--optional-tools' }
Invoke-PhanesCommand $taskPython $taskPythonArguments

$taskNpmCache = Join-Path $taskProjectRoot 'runtime\cache\npm'
foreach ($taskPackageDirectory in @('setup', 'desktop')) {
    Push-Location (Join-Path $taskProjectRoot $taskPackageDirectory)
    try {
        Invoke-PhanesCommand $taskNpm @('ci', '--cache', $taskNpmCache, '--no-audit', '--no-fund')
    } finally {
        Pop-Location
    }
}
$taskMeshopt = Join-Path $taskProjectRoot 'runtime\tools\meshoptimizer'
[System.IO.Directory]::CreateDirectory($taskMeshopt) | Out-Null
foreach ($taskFile in @('meshopt_simplifier.js', 'LICENSE.md')) {
    Copy-Item -LiteralPath (Join-Path $taskProjectRoot "setup\node_modules\meshoptimizer\$taskFile") -Destination $taskMeshopt -Force
}
Copy-Item -LiteralPath $taskNode -Destination (Join-Path $taskMeshopt 'node.exe') -Force
Invoke-PhanesCommand $taskNode @((Join-Path $taskProjectRoot 'desktop\node_modules\electron\install.js'))
Invoke-PhanesCommand $taskNode @((Join-Path $taskProjectRoot 'desktop\package.cjs'))

$taskSettingsDirectory = Join-Path $taskProjectRoot 'local_data'
[System.IO.Directory]::CreateDirectory($taskSettingsDirectory) | Out-Null
$taskSettings = @{ blender = $taskBlender } | ConvertTo-Json
[System.IO.File]::WriteAllText((Join-Path $taskSettingsDirectory 'settings.json'), $taskSettings, [System.Text.UTF8Encoding]::new($false))
if (-not $NoShortcuts) {
    & (Join-Path $taskProjectRoot 'desktop\install-shortcuts.ps1')
}
Write-Host 'Phanes Studio instalado. Abra Start-PhanesStudio.bat ou o atalho.'
if ($SkipModels) {
    Write-Host 'Pesos omitidos: execute novamente sem -SkipModels antes de gerar modelos.'
}
