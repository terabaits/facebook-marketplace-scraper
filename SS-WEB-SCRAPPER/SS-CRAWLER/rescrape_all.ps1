# Re-scrape all categories
$categories = @("gpu", "cpu", "ssd", "ram", "cases")

foreach ($cat in $categories) {
    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host "Scraping $cat..." -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    
    python main.py scrape --$cat --max-pages 0
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "$cat scrape completed successfully!" -ForegroundColor Green
    } else {
        Write-Host "$cat scrape failed!" -ForegroundColor Red
    }
    
    # Small delay between scrapes
    Start-Sleep -Seconds 2
}

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "All scrapes completed!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
