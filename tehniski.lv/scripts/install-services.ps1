# Run as Administrator. Requires nssm.exe on PATH (https://nssm.cc).
# Creates two Windows Services: tehniski-lv-web and tehniski-lv-worker (for M2+).
# Both auto-restart on crash, log to .\logs\.

$ErrorActionPreference = 'Stop'
$projectDir = 'G:\Github\tehniski.lv'
$logDir = Join-Path $projectDir 'logs'
New-Item -ItemType Directory -Path $logDir -Force | Out-Null

# Web service
nssm install tehniski-lv-web 'C:\Program Files\nodejs\node.exe' `
  "$projectDir\node_modules\next\dist\bin\next start -p 5002"
nssm set tehniski-lv-web AppDirectory $projectDir
nssm set tehniski-lv-web AppStdout (Join-Path $logDir 'web.out.log')
nssm set tehniski-lv-web AppStderr (Join-Path $logDir 'web.err.log')
nssm set tehniski-lv-web AppRotateFiles 1
nssm set tehniski-lv-web AppRotateBytes 10485760
nssm set tehniski-lv-web Start SERVICE_AUTO_START
nssm set tehniski-lv-web AppExit Default Restart
nssm set tehniski-lv-web AppRestartDelay 5000
nssm start tehniski-lv-web

Write-Host "tehniski-lv-web installed and started"
Write-Host "Verify: https://localhost:5002/api/health (or via Cloudflare Tunnel)"

# Worker service (separate process, runs npm run worker via tsx)
nssm install tehniski-lv-worker 'C:\Program Files\nodejs\npx.cmd' `
  'tsx worker/index.ts'
nssm set tehniski-lv-worker AppDirectory $projectDir
nssm set tehniski-lv-worker AppStdout (Join-Path $logDir 'worker.out.log')
nssm set tehniski-lv-worker AppStderr (Join-Path $logDir 'worker.err.log')
nssm set tehniski-lv-worker AppRotateFiles 1
nssm set tehniski-lv-worker AppRotateBytes 10485760
nssm set tehniski-lv-worker Start SERVICE_AUTO_START
nssm set tehniski-lv-worker AppExit Default Restart
nssm set tehniski-lv-worker AppRestartDelay 5000
nssm start tehniski-lv-worker

Write-Host "tehniski-lv-worker installed and started"
Write-Host "Verify heartbeat: GET /api/health returns worker_heartbeat_age_seconds"
