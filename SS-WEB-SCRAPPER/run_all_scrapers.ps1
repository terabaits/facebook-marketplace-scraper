# Run the full SS-Crawler scraper across all categories.
# Usage: .\run_all_scrapers.ps1 [-MaxPages 0] [-Limit 0] [-NoBackup]
param(
    [int]$MaxPages = 0,
    [int]$Limit = 0,
    [switch]$NoBackup
)

$venvPython = Join-Path $PSScriptRoot "SS-CRAWLER\venv\Scripts\python.exe"
$main = Join-Path $PSScriptRoot "SS-CRAWLER\main.py"
$categories = @(
    "--gpu", "--cpu", "--ssd", "--ram", "--cases", "--psu",
    "--motherboards", "--monitors", "--consoles", "--lenses",
    "--cameras", "--computers", "--laptops"
)
$args = @("scrape") + $categories + @("--max-pages", $MaxPages)
if ($Limit -gt 0) { $args += @("--limit", $Limit) }
if ($NoBackup) { $args += "--no-backup" }

& $venvPython $main @args
