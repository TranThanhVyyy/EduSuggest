param(
    [string]$BackupLabel = (Get-Date -Format 'yyyyMMdd-HHmmss')
)

$ErrorActionPreference = 'Stop'
$backendDir = Split-Path -Parent $PSScriptRoot
$projectDir = Split-Path -Parent $backendDir
$backupDir = Join-Path $backendDir "database\backups\official-dataset\$BackupLabel"

function Find-PgTool([string]$Name) {
    $command = Get-Command $Name -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }
    $roots = @(
        'C:\Program Files\pgAdmin 4',
        "$env:LOCALAPPDATA\Programs\pgAdmin 4",
        'C:\Program Files\PostgreSQL'
    )
    foreach ($root in $roots) {
        if (-not (Test-Path -LiteralPath $root)) { continue }
        $match = Get-ChildItem -LiteralPath $root -Recurse -Filter "$Name.exe" -File -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($match) { return $match.FullName }
    }
    throw "$Name was not found. Install PostgreSQL client tools before backup."
}

$pgDump = Find-PgTool 'pg_dump'
$pgRestore = Find-PgTool 'pg_restore'
$line = Get-Content -LiteralPath (Join-Path $backendDir '.env') | Where-Object { $_ -match '^DATABASE_URL=' } | Select-Object -First 1
if (-not $line) { throw 'DATABASE_URL was not found in backend/.env.' }
$raw = (($line -replace '^DATABASE_URL=', '').Trim() -replace '^postgresql\+psycopg://','postgresql://')
$uri = [uri]$raw
$parts = $uri.UserInfo.Split(':',2)
$user = [uri]::UnescapeDataString($parts[0])
$password = if ($parts.Count -gt 1) { [uri]::UnescapeDataString($parts[1]) } else { '' }
$database = $uri.AbsolutePath.TrimStart('/')
if ($database -ne 'EduSuggest') { throw "Production backup guard failed: configured database is $database" }

New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
$dumpPath = Join-Path $backupDir 'EduSuggest.custom.dump'
$tempDump = Join-Path $env:TEMP "edusuggest-$BackupLabel.custom.dump"
$env:PGPASSWORD = $password
try {
    & $pgDump --format=custom --no-owner --no-privileges --host=$($uri.Host) --port=$($uri.Port) --username=$user --file=$tempDump EduSuggest
    if ($LASTEXITCODE -ne 0) { throw "pg_dump failed with exit code $LASTEXITCODE" }
    & $pgRestore --list $tempDump | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'pg_restore could not read the custom backup.' }
    Move-Item -LiteralPath $tempDump -Destination $dumpPath -Force
} finally {
    Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $tempDump -Force -ErrorAction SilentlyContinue
}

$mediaArchive = Join-Path $backupDir 'media.zip'
$privateArchive = Join-Path $backupDir 'private-storage.zip'
if (Test-Path -LiteralPath (Join-Path $projectDir 'media')) {
    Compress-Archive -LiteralPath (Join-Path $projectDir 'media') -DestinationPath $mediaArchive -CompressionLevel Optimal
}
if (Test-Path -LiteralPath (Join-Path $backendDir 'private_storage')) {
    Compress-Archive -LiteralPath (Join-Path $backendDir 'private_storage') -DestinationPath $privateArchive -CompressionLevel Optimal
}

$hashes = Get-ChildItem -LiteralPath $backupDir -File | Where-Object Extension -In '.dump','.zip' | ForEach-Object {
    $hash = Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256
    [pscustomobject]@{ file = $_.Name; bytes = $_.Length; sha256 = $hash.Hash.ToLowerInvariant() }
}
$manifest = @{
    database = 'EduSuggest'
    format = 'PostgreSQL custom'
    pg_dump = $pgDump
    created_at = (Get-Date).ToUniversalTime().ToString('o')
    files = @($hashes)
    restore_list_verified = $true
} | ConvertTo-Json -Depth 5
$manifest | Set-Content -LiteralPath (Join-Path $backupDir 'backup-manifest.json') -Encoding UTF8
Write-Output "Backup verified: $backupDir"
$hashes | Format-Table -AutoSize
