$ErrorActionPreference = 'Stop'
$taskProjectRoot = Split-Path -Parent $PSScriptRoot
$taskExecutable = Join-Path $PSScriptRoot 'dist\3DStudio\Phanes Studio.exe'
$taskIcon = Join-Path $PSScriptRoot 'assets\phanes-studio-minimal.ico'

foreach ($taskRequiredFile in @($taskExecutable, $taskIcon)) {
    if (-not (Test-Path -LiteralPath $taskRequiredFile -PathType Leaf)) {
        throw "Arquivo necessário não encontrado: $taskRequiredFile"
    }
}

$taskDesktop = [Environment]::GetFolderPath('DesktopDirectory')
$taskPrograms = [Environment]::GetFolderPath('Programs')
$taskShell = New-Object -ComObject WScript.Shell
$taskShortcuts = @()

foreach ($taskFolder in @($taskDesktop, $taskPrograms)) {
    if (-not $taskFolder) {
        throw 'Não foi possível localizar as pastas de atalhos do usuário.'
    }
    [System.IO.Directory]::CreateDirectory($taskFolder) | Out-Null
    $taskShortcutPath = Join-Path $taskFolder 'Phanes Studio.lnk'
    $taskShortcut = $taskShell.CreateShortcut($taskShortcutPath)
    $taskShortcut.TargetPath = $taskExecutable
    $taskShortcut.WorkingDirectory = $taskProjectRoot
    $taskShortcut.IconLocation = "$taskIcon,0"
    $taskShortcut.Description = 'Phanes Studio — criação de modelos 3D com IA'
    $taskShortcut.WindowStyle = 1
    $taskShortcut.Save()

    $taskSavedShortcut = $taskShell.CreateShortcut($taskShortcutPath)
    if ($taskSavedShortcut.TargetPath -ne $taskExecutable) {
        throw "O atalho não aponta para o executável esperado: $taskShortcutPath"
    }
    $taskShortcuts += [pscustomobject]@{
        path = $taskShortcutPath
        target = $taskSavedShortcut.TargetPath
        workingDirectory = $taskSavedShortcut.WorkingDirectory
        icon = $taskSavedShortcut.IconLocation
    }
}

$taskReportDirectory = Join-Path $taskProjectRoot 'local_data\studio'
[System.IO.Directory]::CreateDirectory($taskReportDirectory) | Out-Null
$taskReport = [pscustomobject]@{
    application = 'Phanes Studio'
    shortcuts = $taskShortcuts
}
$taskReportJson = $taskReport | ConvertTo-Json -Depth 4
$taskReportPath = Join-Path $taskReportDirectory 'phanes-shortcuts-validation.json'
[System.IO.File]::WriteAllText($taskReportPath, $taskReportJson, [System.Text.UTF8Encoding]::new($false))
$taskReportJson
