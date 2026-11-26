param(
    [ValidateRange(1, 500)][int]$TailLines = 30,
    [switch]$Follow
)

$backendDir = Split-Path -Parent $PSScriptRoot
$runtimeDir = Join-Path $backendDir 'logs\assignment-worker'
if (-not (Test-Path -LiteralPath $runtimeDir)) { throw "No worker logs at $runtimeDir" }
$logs = @(Get-ChildItem -LiteralPath $runtimeDir -Filter '*.jsonl' -File | Sort-Object LastWriteTime -Descending)
if ($logs.Count -eq 0) { throw 'No worker JSONL logs found.' }
$logs | Select-Object -First 8 | ForEach-Object { Write-Output "--- $($_.Name) ---"; Get-Content -LiteralPath $_.FullName -Tail $TailLines }
if ($Follow) {
    Write-Output "Following $($logs[0].FullName); press Ctrl+C to stop monitoring."
    Get-Content -LiteralPath $logs[0].FullName -Wait -Tail $TailLines
}
