param(
    [switch]$KeepFixtures
)

$ErrorActionPreference = 'Stop'
$backendDir = Split-Path -Parent $PSScriptRoot
$python = Join-Path $backendDir 'venv\Scripts\python.exe'
$runtimeDir = Join-Path $backendDir 'logs\gd382-staging'
$manifestPath = Join-Path $runtimeDir 'staging-processes.json'

& (Join-Path $PSScriptRoot 'stop_assignment_worker.ps1') -TimeoutSeconds 30
if ($LASTEXITCODE -ne 0) { throw 'Assignment worker did not stop gracefully; inspect its PID files before cleanup.' }

if (Test-Path -LiteralPath $manifestPath) {
    $manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
    if ($manifest.database -ne 'EduSuggest_phase3_test') { throw 'Staging process manifest database guard failed.' }
    foreach ($entryName in @('frontend', 'backend')) {
        $entry = $manifest.$entryName
        $process = Get-Process -Id ([int]$entry.pid) -ErrorAction SilentlyContinue
        if (-not $process) { continue }
        $recorded = [datetime]::Parse([string]$entry.started_at).ToUniversalTime().Ticks
        if ($process.StartTime.ToUniversalTime().Ticks -ne $recorded) {
            throw "PID reuse guard failed for $entryName PID $($entry.pid); refusing to stop it."
        }
        Stop-Process -Id $process.Id
        if (-not $process.WaitForExit(10000)) { Stop-Process -Id $process.Id -Force }
        Write-Output "Stopped $entryName PID $($entry.pid)"
    }
    Remove-Item -LiteralPath $manifestPath -Force
}

if (-not $KeepFixtures) {
    & $python (Join-Path $PSScriptRoot 'cleanup_gd382_browser_fixtures.py')
    if ($LASTEXITCODE -ne 0) { throw 'Fixture cleanup failed; inspect the fixture manifest before retrying.' }
}

foreach ($port in @(8001, 5174)) {
    if (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) {
        throw "Port $port is still listening; verify the process manually."
    }
}
Write-Output 'GĐ3.8.2 staging stopped safely.'
