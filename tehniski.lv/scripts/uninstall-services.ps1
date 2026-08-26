$ErrorActionPreference = 'SilentlyContinue'
nssm stop tehniski-lv-web
nssm remove tehniski-lv-web confirm
Write-Host "tehniski-lv-web removed"
