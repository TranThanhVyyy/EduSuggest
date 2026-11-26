param(
    [ValidateRange(1, 8)][int]$WorkerCount = 1,
    [ValidateRange(1, 60)][int]$PollIntervalSeconds = 5
)

$ErrorActionPreference = 'Stop'
$backendDir = Split-Path -Parent $PSScriptRoot
$python = Join-Path $backendDir 'venv\Scripts\python.exe'
$runtimeDir = Join-Path $backendDir 'logs\assignment-worker'
if (-not (Test-Path -LiteralPath $python)) { throw "Backend virtualenv Python not found: $python" }
New-Item -ItemType Directory -Path $runtimeDir -Force | Out-Null

# Process-only settings: no project .env file is edited.
$env:DEBUG = 'False'
$env:AUTO_ASSIGNMENT_WORKFLOW_ENABLED = 'True'
$env:AUTO_ASSIGNMENT_WORKER_ENABLED = 'True'
$env:ACCOUNTABILITY_ENABLED = 'True'

for ($i = 0; $i -lt $WorkerCount; $i++) {
    $workerId = "stage-$([guid]::NewGuid().ToString('N').Substring(0,8))"
    $logPath = Join-Path $runtimeDir "$workerId.jsonl"
    $workerArgs = @(
        ('"' + (Join-Path $PSScriptRoot 'run_assignment_worker.py') + '"'),
        '--expected-database', 'EduSuggest_phase3_test',
        '--poll-interval', "$PollIntervalSeconds",
        '--worker-id', $workerId,
        '--log-file', ('"' + $logPath + '"'),
        '--control-dir', ('"' + $runtimeDir + '"')
    )
    $process = Start-Process -FilePath $python -ArgumentList $workerArgs -WorkingDirectory $backendDir -WindowStyle Hidden -PassThru
    $deadline = (Get-Date).AddSeconds(10)
    $workerMetadata = $null
    while ((Get-Date) -lt $deadline -and -not $workerMetadata) {
        foreach ($pidFile in Get-ChildItem -LiteralPath $runtimeDir -Filter 'worker-*.pid' -File) {
            try {
                $candidate = Get-Content -LiteralPath $pidFile.FullName -Raw | ConvertFrom-Json
                if ($candidate.worker_id -eq $workerId) { $workerMetadata = $candidate; break }
            } catch { }
        }
        if (-not (Get-Process -Id $process.Id -ErrorAction SilentlyContinue)) {
            Get-Content -LiteralPath $logPath -ErrorAction SilentlyContinue | Select-Object -Last 10
            throw "Worker exited before registering its PID; inspect $logPath"
        }
        Start-Sleep -Milliseconds 250
    }
    if (-not $workerMetadata) { throw "Worker did not become ready; inspect $logPath" }
    Write-Output "Started workerId=$workerId pid=$($workerMetadata.pid) database=$($workerMetadata.database) log=$logPath"
}
