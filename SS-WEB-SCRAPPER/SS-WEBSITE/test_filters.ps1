# Test GPU vendor filter
Write-Host "Testing GPU Vendor Filter..."

# Test with NVIDIA
$response1 = Invoke-WebRequest -Uri "http://localhost:5000/api/gpus?active=true&vendor=NVIDIA" -UseBasicParsing
$data1 = $response1.Content | ConvertFrom-Json
$nvidiaCount = ($data1 | Where-Object { $_.vendor -eq "NVIDIA" }).Count
$amdCount = ($data1 | Where-Object { $_.vendor -eq "AMD" }).Count
$total = $data1.Count

Write-Host "Vendor=NVIDIA filter results:"
Write-Host "  Total: $total"
Write-Host "  NVIDIA: $nvidiaCount"
Write-Host "  AMD: $amdCount"
if ($amdCount -eq 0 -and $nvidiaCount -gt 0) {
    Write-Host "  ✓ NVIDIA filter WORKING"
} else {
    Write-Host "  ✗ NVIDIA filter NOT WORKING"
}

# Test with AMD
$response2 = Invoke-WebRequest -Uri "http://localhost:5000/api/gpus?active=true&vendor=AMD" -UseBasicParsing
$data2 = $response2.Content | ConvertFrom-Json
$nvidiaCount2 = ($data2 | Where-Object { $_.vendor -eq "NVIDIA" }).Count
$amdCount2 = ($data2 | Where-Object { $_.vendor -eq "AMD" }).Count
$total2 = $data2.Count

Write-Host "`nVendor=AMD filter results:"
Write-Host "  Total: $total2"
Write-Host "  NVIDIA: $nvidiaCount2"
Write-Host "  AMD: $amdCount2"
if ($nvidiaCount2 -eq 0 -and $amdCount2 -gt 0) {
    Write-Host "  ✓ AMD filter WORKING"
} else {
    Write-Host "  ✗ AMD filter NOT WORKING"
}

# Test VRAM filter
Write-Host "`nTesting VRAM Filter..."
$response3 = Invoke-WebRequest -Uri "http://localhost:5000/api/gpus?active=true&vram=8" -UseBasicParsing
$data3 = $response3.Content | ConvertFrom-Json
$vram8 = ($data3 | Where-Object { $_.vram_gb -eq 8 }).Count
$not8 = ($data3 | Where-Object { $_.vram_gb -ne 8 }).Count
$total3 = $data3.Count

Write-Host "VRAM=8 filter results:"
Write-Host "  Total: $total3"
Write-Host "  8GB: $vram8"
Write-Host "  Other: $not8"
if ($not8 -eq 0 -and $vram8 -gt 0) {
    Write-Host "  ✓ VRAM filter WORKING"
} else {
    Write-Host "  ✗ VRAM filter NOT WORKING"
}
