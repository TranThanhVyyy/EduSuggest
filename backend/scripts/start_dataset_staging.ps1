param(
    [int]$BackendPort = 8002,
    [int]$FrontendPort = 5175
)

$ErrorActionPreference = 'Stop'
$backendDir = Split-Path -Parent $PSScriptRoot
$projectDir = Split-Path -Parent $backendDir
$frontendDir = Join-Path $projectDir 'frontend'
$python = Join-Path $backendDir 'venv\Scripts\python.exe'
$runtimeDir = Join-Path $backendDir 'logs\official-dataset\staging'
$manifestPath = Join-Path $runtimeDir 'processes.json'
$mediaDir = Join-Path $projectDir 'media\dataset-staging\courses'
$viteCache = Join-Path $frontendDir 'node_modules\.vite-dataset-staging'

if (-not (Test-Path -LiteralPath $python)) { throw "Backend Python not found: $python" }
if (Test-Path -LiteralPath $manifestPath) { throw "Dataset staging manifest already exists: $manifestPath" }
foreach ($port in @($BackendPort, $FrontendPort)) {
    if (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) {
        throw "Port $port is already listening; refusing to stop or replace an unrelated process."
    }
}
New-Item -ItemType Directory -Path $runtimeDir,$mediaDir,$viteCache -Force | Out-Null

$sourceUrl = Get-Content -LiteralPath (Join-Path $backendDir '.env') |
    Where-Object { $_ -match '^DATABASE_URL=' } |
    Select-Object -First 1
if (-not $sourceUrl) { throw 'DATABASE_URL was not found in backend/.env.' }
$normalizedUrl = (($sourceUrl -replace '^DATABASE_URL=', '').Trim() -replace '^postgresql\+psycopg://', 'postgresql://')
$builder = [System.UriBuilder]$normalizedUrl
$builder.Path = '/EduSuggest_dataset_staging'
$env:DATABASE_URL = ($builder.Uri.AbsoluteUri -replace '^postgresql://', 'postgresql+psycopg://')
$env:DEBUG = 'False'
$env:FRONTEND_URL = "http://127.0.0.1:$FrontendPort"
$env:BACKEND_URL = "http://127.0.0.1:$BackendPort"
$env:EXPERT_MANAGEMENT_ENABLED = 'True'
$env:AUTO_ASSIGNMENT_WORKFLOW_ENABLED = 'True'
$env:AUTO_ASSIGNMENT_WORKER_ENABLED = 'False'
$env:ACCOUNTABILITY_ENABLED = 'True'
$env:EDUSUGGEST_COURSE_MEDIA_DIR = $mediaDir

& $python -c "from sqlalchemy import create_engine,text; import os; e=create_engine(os.environ['DATABASE_URL']); c=e.connect(); d=c.execute(text('select current_database()')).scalar_one(); r=c.execute(text('select version_num from alembic_version')).scalar_one(); print('database='+d+' revision='+r); assert d == 'EduSuggest_dataset_staging'; assert r == 'c3d4e5f6a7b8'; c.close(); e.dispose()"
if ($LASTEXITCODE -ne 0) { throw 'Dataset database identity guard failed.' }

$started = @()
try {
    $apiOut = Join-Path $runtimeDir 'backend.stdout.log'
    $apiErr = Join-Path $runtimeDir 'backend.stderr.log'
    $api = Start-Process -FilePath $python -ArgumentList @('-m','uvicorn','main:app','--host','127.0.0.1','--port',"$BackendPort") -WorkingDirectory $backendDir -WindowStyle Hidden -RedirectStandardOutput $apiOut -RedirectStandardError $apiErr -PassThru
    $started += $api

    $env:VITE_API_BASE_URL = "http://127.0.0.1:$BackendPort/api"
    $env:VITE_CACHE_DIR = $viteCache
    $vite = Join-Path $frontendDir 'node_modules\vite\bin\vite.js'
    $frontOut = Join-Path $runtimeDir 'frontend.stdout.log'
    $frontErr = Join-Path $runtimeDir 'frontend.stderr.log'
    $front = Start-Process -FilePath 'node.exe' -ArgumentList @(('"' + $vite + '"'),'--host','127.0.0.1','--port',"$FrontendPort",'--strictPort') -WorkingDirectory $frontendDir -WindowStyle Hidden -RedirectStandardOutput $frontOut -RedirectStandardError $frontErr -PassThru
    $started += $front

    $deadline = (Get-Date).AddSeconds(30)
    $health = $null
    $frontend = $null
    do {
        try {
            $health = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:$BackendPort/api/health" -TimeoutSec 2
            $frontend = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:$FrontendPort/" -TimeoutSec 2
        } catch { Start-Sleep -Milliseconds 500 }
    } while ((Get-Date) -lt $deadline -and ($health.StatusCode -ne 200 -or $frontend.StatusCode -ne 200))
    if ($health.StatusCode -ne 200 -or $frontend.StatusCode -ne 200) { throw 'Dataset staging HTTP readiness failed.' }

    @{
        database = 'EduSuggest_dataset_staging'
        backend_port = $BackendPort
        frontend_port = $FrontendPort
        backend = @{ pid = $api.Id; started_at = $api.StartTime.ToUniversalTime().ToString('o') }
        frontend = @{ pid = $front.Id; started_at = $front.StartTime.ToUniversalTime().ToString('o') }
        media_dir = $mediaDir
        vite_cache = $viteCache
        created_at = (Get-Date).ToUniversalTime().ToString('o')
    } | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $manifestPath -Encoding UTF8
    Write-Output "Official dataset staging ready: http://127.0.0.1:$FrontendPort/"
    Write-Output "API: http://127.0.0.1:$BackendPort/api; database: EduSuggest_dataset_staging"
    Write-Output "Credentials: $backendDir\logs\official-dataset\demo-credentials.json"
} catch {
    foreach ($process in $started) {
        if (Get-Process -Id $process.Id -ErrorAction SilentlyContinue) { Stop-Process -Id $process.Id -Force }
    }
    throw
}
