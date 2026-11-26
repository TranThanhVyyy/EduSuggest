param([ValidateRange(1, 120)][int]$TimeoutSeconds = 20)

$ErrorActionPreference = 'Stop'
$backendDir = Split-Path -Parent $PSScriptRoot
$runtimeDir = Join-Path $backendDir 'logs\assignment-worker'
if (-not (Test-Path -LiteralPath $runtimeDir)) { Write-Output 'No worker runtime directory.'; exit 0 }

$workers = Get-ChildItem -LiteralPath $runtimeDir -Filter 'worker-*.pid' -File
foreach ($file in $workers) {
    $pidValue = 0
    try { $pidValue = [int](Get-Content -LiteralPath $file.FullName -Raw | ConvertFrom-Json).pid }
    catch { Write-Warning "Invalid worker pid metadata: $($file.Name)"; continue }
    if (-not (Get-Process -Id $pidValue -ErrorAction SilentlyContinue)) {
        Remove-Item -LiteralPath $file.FullName -Force
        Remove-Item -LiteralPath (Join-Path $runtimeDir "worker-$pidValue.stop") -Force -ErrorAction SilentlyContinue
        Write-Output "Removed stale pid file pid=$pidValue"
        continue
    }
    $stopFile = Join-Path $runtimeDir "worker-$pidValue.stop"
    New-Item -ItemType File -Path $stopFile -Force | Out-Null
    Write-Output "Requested graceful stop pid=$pidValue"
}

$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
do {
    $remaining = @(Get-ChildItem -LiteralPath $runtimeDir -Filter 'worker-*.pid' -File)
    if ($remaining.Count -eq 0) { Write-Output 'All assignment workers stopped.'; exit 0 }
    Start-Sleep -Milliseconds 500
} while ((Get-Date) -lt $deadline)

Write-Warning "Graceful stop timed out; worker pid files remain: $($remaining.Name -join ', ')"
exit 1
