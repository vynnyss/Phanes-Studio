# Opened only by the user's explicit "Escolher pasta" action.
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
Add-Type -AssemblyName System.Windows.Forms
$taskPicker = New-Object System.Windows.Forms.FolderBrowserDialog
$taskPicker.Description = 'Escolher pasta para exportar LODs'
$taskPicker.ShowNewFolderButton = $true
$taskResult = $taskPicker.ShowDialog()
$taskDirectory = ''
if ($taskResult -eq [System.Windows.Forms.DialogResult]::OK) {
    $taskDirectory = $taskPicker.SelectedPath
}
$taskPicker.Dispose()
@{ directory = $taskDirectory } | ConvertTo-Json -Compress
