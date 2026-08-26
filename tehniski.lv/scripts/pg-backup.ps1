# Daily pg_dump to local backups folder. Schedule via Windows Task Scheduler.
# Recommended: run at 03:00 daily, keep 7 days of backups locally.
# .env is loaded to read DATABASE_URL.
$ErrorActionPreference = 'Stop'
$projectDir = 'G:\Github\tehniski.lv'
Set-Location $projectDir

# Load DATABASE_URL from .env
$envFile = Join-Path $projectDir '.env'
if (Test-Path $envFile) {
  Get-Content $envFile | ForEach-Object {
    if ($_ -match '^\s*DATABASE_URL\s*=\s*(.+?)\s*$') {
      $env:DATABASE_URL = $matches[1]
    }
  }
}

if (-not $env:DATABASE_URL) {
  throw "DATABASE_URL not found in .env"
}

# Parse DATABASE_URL: postgresql://user:password@host:port/database
$regex = 'postgresql://(?<user>[^:]+):(?<pass>[^@]+)@(?<host>[^:]+):(?<port>\d+)/(?<db>[^?]+)'
$m = [regex]::Match($env:DATABASE_URL, $regex)
if (-not $m.Success) { throw "Could not parse DATABASE_URL" }

$user = $m.Groups['user'].Value
$pass = $m.Groups['pass'].Value
$host = $m.Groups['host'].Value
$port = $m.Groups['port'].Value
$db   = $m.Groups['db'].Value

$backupDir = Join-Path $projectDir 'backups'
New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
$timestamp = Get-Date -Format 'yyyy-MM-dd-HHmm'
$out = Join-Path $backupDir "$db-$timestamp.sql.gz"

$env:PGPASSWORD = $pass
& pg_dump -h $host -p $port -U $user -d $db --no-owner | gzip > $out

# Retention: delete local backups older than 7 days
Get-ChildItem $backupDir -Filter '*.sql.gz' | Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-7) } | Remove-Item

Write-Host "Backup created: $out"
