param(
    [ValidateRange(1, 4)][int]$WorkerCount = 1
)

$ErrorActionPreference = 'Stop'
$backendDir = Split-Path -Parent $PSScriptRoot
$projectDir = Split-Path -Parent $backendDir
$frontendDir = Join-Path $projectDir 'frontend'
$python = Join-Path $backendDir 'venv\Scripts\python.exe'
$runtimeDir = Join-Path $backendDir 'logs\gd382-staging'
$manifestPath = Join-Path $runtimeDir 'staging-processes.json'

if (-not (Test-Path -LiteralPath $python)) { throw "Backend virtualenv Python not found: $python" }
if (Test-Path -LiteralPath $manifestPath) { throw "Staging process manifest already exists: $manifestPath" }
foreach ($port in @(8001, 5174)) {
    if (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) {
        throw "Port $port is already listening; refusing to affect an unrelated process."
    }
}

New-Item -ItemType Directory -Path $runtimeDir -Force | Out-Null
$started = @()
try {
    # Fixture preparation resolves and verifies EduSuggest_phase3_test internally.
    & $python (Join-Path $PSScriptRoot 'prepare_gd382_browser_fixtures.py')
    if ($LASTEXITCODE -ne 0) { throw 'Browser fixture preparation failed.' }

    $sourceUrl = Get-Content -LiteralPath (Join-Path $backendDir '.env') |
        Where-Object { $_ -match '^DATABASE_URL=' } |
        Select-Object -First 1
    if (-not $sourceUrl) { throw 'DATABASE_URL was not found in backend/.env.' }
    $builder = [System.UriBuilder](($sourceUrl -replace '^DATABASE_URL=', '').Trim())
    $builder.Path = '/EduSuggest_phase3_test'

    # Process-only configuration. No project configuration file is modified.
    $env:DATABASE_URL = $builder.Uri.AbsoluteUri
    $env:DEBUG = 'False'
    $env:EXPERT_MANAGEMENT_ENABLED = 'True'
    $env:AUTO_ASSIGNMENT_WORKFLOW_ENABLED = 'True'
    $env:AUTO_ASSIGNMENT_WORKER_ENABLED = 'True'
    $env:ACCOUNTABILITY_ENABLED = 'True'
    $env:FRONTEND_URL = 'http://127.0.0.1:5174'
    $env:BACKEND_URL = 'http://127.0.0.1:8001'

    & $python -c "from sqlalchemy import create_engine,text; import os; e=create_engine(os.environ['DATABASE_URL']); c=e.connect(); d=c.execute(text('select current_database()')).scalar_one(); print('database='+d); assert d == 'EduSuggest_phase3_test'; c.close(); e.dispose()"
    if ($LASTEXITCODE -ne 0) { throw 'Database identity guard failed.' }

    $apiOut = Join-Path $runtimeDir 'backend.stdout.log'
    $apiErr = Join-Path $runtimeDir 'backend.stderr.log'
    $apiArgs = @('-m', 'uvicorn', 'main:app', '--host', '127.0.0.1', '--port', '8001')
    $api = Start-Process -FilePath $python -ArgumentList $apiArgs -WorkingDirectory $backendDir -WindowStyle Hidden -RedirectStandardOutput $apiOut -RedirectStandardError $apiErr -PassThru
    $started += $api

    $env:VITE_API_BASE_URL = 'http://127.0.0.1:8001/api'
    $vite = Join-Path $frontendDir 'node_modules\vite\bin\vite.js'
    if (-not (Test-Path -LiteralPath $vite)) { throw "Vite runtime not found: $vite" }
    $frontOut = Join-Path $runtimeDir 'frontend.stdout.log'
    $frontErr = Join-Path $runtimeDir 'frontend.stderr.log'
    $viteArgs = @(('"' + $vite + '"'), '--host', '127.0.0.1', '--port', '5174', '--strictPort')
    $front = Start-Process -FilePath 'node.exe' -ArgumentList $viteArgs -WorkingDirectory $frontendDir -WindowStyle Hidden -RedirectStandardOutput $frontOut -RedirectStandardError $frontErr -PassThru
    $started += $front

    & (Join-Path $PSScriptRoot 'start_assignment_worker.ps1') -WorkerCount $WorkerCount -PollIntervalSeconds 1
    if ($LASTEXITCODE -ne 0) { throw 'Assignment worker startup failed.' }

    $deadline = (Get-Date).AddSeconds(30)
    do {
        try {
            $health = Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:8001/api/health' -TimeoutSec 2
            $frontend = Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:5174/' -TimeoutSec 2
        } catch {
            Start-Sleep -Milliseconds 500
        }
    } while ((Get-Date) -lt $deadline -and ($health.StatusCode -ne 200 -or $frontend.StatusCode -ne 200))
    if ($health.StatusCode -ne 200 -or $frontend.StatusCode -ne 200) { throw 'Staging HTTP readiness check failed.' }

    @{
        database = 'EduSuggest_phase3_test'
        backend = @{ pid = $api.Id; started_at = $api.StartTime.ToUniversalTime().ToString('o') }
        frontend = @{ pid = $front.Id; started_at = $front.StartTime.ToUniversalTime().ToString('o') }
        created_at = (Get-Date).ToUniversalTime().ToString('o')
    } | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $manifestPath -Encoding UTF8

    Write-Output 'GĐ3.8.2 staging is ready: http://127.0.0.1:5174/'
    Write-Output "Database: EduSuggest_phase3_test; worker count: $WorkerCount"
    Write-Output "Fixture credentials: $runtimeDir\fixtures.json"
    Write-Output "Stop safely: powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$PSScriptRoot\stop_gd382_staging.ps1`""
} catch {
    foreach ($process in $started) {
        if (Get-Process -Id $process.Id -ErrorAction SilentlyContinue) { Stop-Process -Id $process.Id -Force }
    }
    & (Join-Path $PSScriptRoot 'stop_assignment_worker.ps1') -TimeoutSeconds 10
    throw
}
