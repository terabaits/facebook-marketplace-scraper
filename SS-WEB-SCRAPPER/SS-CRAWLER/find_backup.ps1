# Search for PostgreSQL backup files
$searchPaths = @(
    "$env:USERPROFILE\Documents",
    "$env:USERPROFILE\Downloads", 
    "$env:USERPROFILE\Desktop",
    "G:\",
    "C:\Program Files\PostgreSQL",
    "C:\ProgramData"
)

$backupPatterns = @("*.sql", "*.backup", "*.dump", "*.pgdump", "*ss_market*", "*postgres*")

Write-Host "Searching for PostgreSQL backup files..." -ForegroundColor Cyan
Write-Host "=" * 60

$found = $false
foreach ($path in $searchPaths) {
    if (Test-Path $path) {
        foreach ($pattern in $backupPatterns) {
            $files = Get-ChildItem -Path $path -Filter $pattern -Recurse -ErrorAction SilentlyContinue | 
                     Sort-Object LastWriteTime -Descending | 
                     Select-Object -First 10
            
            foreach ($file in $files) {
                Write-Host "Found: $($file.FullName)" -ForegroundColor Green
                Write-Host "  Size: $([math]::Round($file.Length / 1MB, 2)) MB"
                Write-Host "  Modified: $($file.LastWriteTime)"
                Write-Host ""
                $found = $true
            }
        }
    }
}

if (-not $found) {
    Write-Host "No backup files found in common locations." -ForegroundColor Yellow
}

Write-Host "=" * 60
Write-Host "Also check pg_dump location:" -ForegroundColor Cyan

# Check if pg_dump exists
$pgDumpPaths = @(
    "C:\Program Files\PostgreSQL\*\bin\pg_dump.exe",
    "C:\Program Files (x86)\PostgreSQL\*\bin\pg_dump.exe"
)

foreach ($pgPath in $pgDumpPaths) {
    $foundPath = Get-ChildItem -Path $pgPath -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($foundPath) {
        Write-Host "pg_dump found: $($foundPath.FullName)" -ForegroundColor Green
    }
}
