param(
    [Parameter(Mandatory=$true)][string]$BackupDirectory
)

$ErrorActionPreference = 'Stop'
$backendDir = Split-Path -Parent $PSScriptRoot
$python = Join-Path $backendDir 'venv\Scripts\python.exe'
$dumpPath = Join-Path $BackupDirectory 'EduSuggest.custom.dump'
$manifestPath = Join-Path $BackupDirectory 'backup-manifest.json'
if (-not (Test-Path -LiteralPath $dumpPath) -or -not (Test-Path -LiteralPath $manifestPath)) { throw 'Backup dump or manifest is missing.' }
$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
if ($manifest.database -ne 'EduSuggest' -or $manifest.format -ne 'PostgreSQL custom') { throw 'Backup manifest guard failed.' }
$expected = ($manifest.files | Where-Object file -eq 'EduSuggest.custom.dump').sha256
$actual = (Get-FileHash -LiteralPath $dumpPath -Algorithm SHA256).Hash.ToLowerInvariant()
if ($expected -ne $actual) { throw 'Backup SHA-256 verification failed.' }
$tempDump = Join-Path $env:TEMP 'edusuggest-official-restore.custom.dump'
Copy-Item -LiteralPath $dumpPath -Destination $tempDump -Force

function Find-PgTool([string]$Name) {
    $command = Get-Command $Name -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }
    foreach ($root in @('C:\Program Files\pgAdmin 4',"$env:LOCALAPPDATA\Programs\pgAdmin 4",'C:\Program Files\PostgreSQL')) {
        if (Test-Path -LiteralPath $root) {
            $match = Get-ChildItem -LiteralPath $root -Recurse -Filter "$Name.exe" -File -ErrorAction SilentlyContinue | Select-Object -First 1
            if ($match) { return $match.FullName }
        }
    }
    throw "$Name was not found."
}
$psql = Find-PgTool 'psql'
$pgRestore = Find-PgTool 'pg_restore'
$line = Get-Content -LiteralPath (Join-Path $backendDir '.env') | Where-Object { $_ -match '^DATABASE_URL=' } | Select-Object -First 1
$raw = (($line -replace '^DATABASE_URL=', '').Trim() -replace '^postgresql\+psycopg://','postgresql://')
$uri = [uri]$raw
$parts = $uri.UserInfo.Split(':',2)
$user = [uri]::UnescapeDataString($parts[0])
$password = if ($parts.Count -gt 1) { [uri]::UnescapeDataString($parts[1]) } else { '' }
$env:PGPASSWORD = $password
try {
    & $python (Join-Path $PSScriptRoot 'create_dataset_database.py')
    if ($LASTEXITCODE -ne 0) { throw 'Dataset database creation/normalization failed.' }
    $tableCount = & $psql --host=$($uri.Host) --port=$($uri.Port) --username=$user --dbname=EduSuggest_dataset_staging --tuples-only --no-align --set=ON_ERROR_STOP=1 --command="SELECT count(*) FROM pg_tables WHERE schemaname='public';"
    if ([int]($tableCount | Select-Object -Last 1) -ne 0) { throw 'EduSuggest_dataset_staging is not empty; refusing to overwrite or restore into it.' }
    $tempSql = Join-Path $env:TEMP 'edusuggest-official-restore.sql'
    & $pgRestore --no-owner --no-privileges --file=$tempSql $tempDump
    if ($LASTEXITCODE -ne 0) { throw 'pg_restore SQL extraction failed.' }
    # PG17 pg_dump (bundled with pgAdmin 4) emits SET transaction_timeout = 0; which PG16 rejects.
    $sqlLines = Get-Content -LiteralPath $tempSql -Encoding UTF8 | Where-Object { $_ -notmatch '^SET transaction_timeout\s*=' }
    [System.IO.File]::WriteAllLines($tempSql, [string[]]$sqlLines, [System.Text.UTF8Encoding]::new($false))
    & $psql --host=$($uri.Host) --port=$($uri.Port) --username=$user --dbname=EduSuggest_dataset_staging --set=ON_ERROR_STOP=1 --file=$tempSql | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'psql restore failed; database was left intact for diagnosis and was not dropped.' }
    Remove-Item -LiteralPath $tempSql -Force -ErrorAction SilentlyContinue
    $identity = & $psql --host=$($uri.Host) --port=$($uri.Port) --username=$user --dbname=EduSuggest_dataset_staging --tuples-only --no-align --set=ON_ERROR_STOP=1 --command="SELECT current_database() || ' ' || version_num FROM alembic_version;"
    if ($LASTEXITCODE -ne 0 -or ($identity | Select-Object -Last 1).Trim() -ne 'EduSuggest_dataset_staging c3d4e5f6a7b8') { throw 'Restored database identity/revision verification failed.' }
    Write-Output "database=$($identity | Select-Object -Last 1)"
} finally {
    Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $tempDump -Force -ErrorAction SilentlyContinue
}
Write-Output 'Restore rehearsal PASS: EduSuggest_dataset_staging is ready and production was not modified.'
