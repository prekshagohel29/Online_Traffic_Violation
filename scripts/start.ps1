param([switch]$Rebuild)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$projectPython = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $projectPython)) { throw 'Run .\scripts\setup.ps1 first.' }
Set-Location -LiteralPath $projectRoot
if ($Rebuild -or -not (Test-Path -LiteralPath 'frontend\build\index.html')) {
    if (-not (Test-Path -LiteralPath 'frontend\node_modules')) { npm --prefix frontend ci --ignore-scripts --no-audit --no-fund }
    if ($LASTEXITCODE -and $LASTEXITCODE -ne 0) { throw 'React dependency installation failed.' }
    $env:REACT_APP_API_BASE_URL = 'http://127.0.0.1:5000'
    $env:CI = 'true'
    npm --prefix frontend run build
    if ($LASTEXITCODE -ne 0) { throw 'React build failed.' }
}
Write-Host 'e-Memo: http://127.0.0.1:3001. Keep this terminal open; Ctrl+C stops the local app.'
& $projectPython -m scripts.local_server
