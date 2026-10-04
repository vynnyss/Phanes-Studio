param([Parameter(Mandatory=$true)][string]$TestName)
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path $PSScriptRoot -Parent
$taskOutput = Join-Path $taskRoot "outputs\$TestName"
$taskReport = Join-Path $taskOutput 'report.json'
$taskRows = [System.Collections.Generic.List[object]]::new()
$taskWatch = [System.Diagnostics.Stopwatch]::StartNew()
while ($true) {
    $taskState = Get-Content -LiteralPath $taskReport -Raw | ConvertFrom-Json
    if ($taskState.result -ne 'running') { break }
    $taskPids = @(Get-Process python -ErrorAction SilentlyContinue |
        Where-Object { $_.Path -like "$taskRoot\runtime\official*" } |
        ForEach-Object Id)
    $taskSample = Get-Counter -Counter '\GPU Process Memory(*)\Dedicated Usage','\GPU Process Memory(*)\Shared Usage' -ErrorAction SilentlyContinue
    $taskDedicated = 0.0
    $taskShared = 0.0
    foreach ($taskCounter in $taskSample.CounterSamples) {
        if ($taskCounter.InstanceName -match '^pid_(\d+)_') {
            $taskPid = [int]$Matches[1]
            if ($taskPids -contains $taskPid) {
                if ($taskCounter.Path -like '*\Dedicated Usage') {
                    $taskDedicated += $taskCounter.CookedValue
                }
                if ($taskCounter.Path -like '*\Shared Usage') {
                    $taskShared += $taskCounter.CookedValue
                }
            }
        }
    }
    $taskRow = [pscustomobject]@{
        timestamp = [DateTimeOffset]::Now.ToString('o')
        elapsed_s = $taskWatch.Elapsed.TotalSeconds
        dedicated_bytes = $taskDedicated
        shared_bytes = $taskShared
        pids = ($taskPids -join ',')
    }
    $taskRow | Export-Csv -LiteralPath (Join-Path $taskOutput 'wddm-memory.csv') -Append -NoTypeInformation
    $taskRows.Add($taskRow)
    Start-Sleep -Seconds 1
}
[pscustomobject]@{
    dedicated_peak_bytes = ($taskRows | Measure-Object dedicated_bytes -Maximum).Maximum
    shared_peak_bytes = ($taskRows | Measure-Object shared_bytes -Maximum).Maximum
    samples = $taskRows.Count
    full_test_coverage = $false
    coverage_reason = 'Monitor started after test initialization; first seconds excluded; sampled WDDM values are not exact CUDA allocator maxima'
} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $taskOutput 'wddm-summary.json') -Encoding utf8
