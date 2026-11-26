$ErrorActionPreference = 'Stop'
$backendDir = Split-Path -Parent $PSScriptRoot
$runtimeDir = Join-Path $backendDir 'logs\official-dataset\staging'
$manifestPath = Join-Path $runtimeDir 'processes.json'

if (-not (Test-Path -LiteralPath $manifestPath)) {
    Write-Output 'No official dataset staging process manifest exists.'
    exit 0
}
$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
if ($manifest.database -ne 'EduSuggest_dataset_staging') { throw 'Dataset staging process guard failed.' }
foreach ($entryName in @('frontend','backend')) {
    $entry = $manifest.$entryName
    $process = Get-Process -Id ([int]$entry.pid) -ErrorAction SilentlyContinue
    if (-not $process) { continue }
    $recorded = [datetime]::Parse([string]$entry.started_at).ToUniversalTime().Ticks
    if ($process.StartTime.ToUniversalTime().Ticks -ne $recorded) {
        throw "PID reuse guard failed for $entryName PID $($entry.pid)."
    }
    Stop-Process -Id $process.Id
    if (-not $process.WaitForExit(10000)) { Stop-Process -Id $process.Id -Force }
    Write-Output "Stopped $entryName PID $($entry.pid)"
}
Remove-Item -LiteralPath $manifestPath -Force
foreach ($port in @([int]$manifest.backend_port,[int]$manifest.frontend_port)) {
    if (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) {
        throw "Port $port is still listening; inspect it manually."
    }
}
Write-Output 'Official dataset staging stopped. Dataset and assets were preserved.'
