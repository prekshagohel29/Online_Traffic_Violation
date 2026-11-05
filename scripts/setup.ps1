param([switch]$SkipModels)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) { python -m venv .venv }
& '.\.venv\Scripts\python.exe' -m pip install -r backend/requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Python dependency installation failed' }
if (-not (Test-Path -LiteralPath '.env')) {
    $secretBytes = New-Object byte[] 48
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($secretBytes)
    $taskSecret = [Convert]::ToBase64String($secretBytes)
    [IO.File]::WriteAllText((Join-Path $projectRoot '.env'), "APP_ENV=local`nJWT_SECRET_KEY=$taskSecret`nDATA_DIR=$($projectRoot.Replace('\','/'))/data`nSTORAGE_MODE=local`nFRONTEND_URL=http://localhost:3000`nCORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,http://127.0.0.1:3001`n")
}
if (-not $SkipModels) {
    foreach ($taskModule in @('scripts.fetch_assets','scripts.fetch_plate_models','scripts.fetch_showcase')) {
        & '.\.venv\Scripts\python.exe' -m $taskModule
        if ($LASTEXITCODE -ne 0) { throw 'Asset provisioning failed' }
    }
}
& '.\.venv\Scripts\python.exe' -m backend.manage init
Set-Location -LiteralPath (Join-Path $projectRoot 'frontend')
npm ci --ignore-scripts --no-audit --no-fund
if ($LASTEXITCODE -ne 0) { throw 'React dependency installation failed' }
Write-Host 'Ready. Run scripts/start.ps1 -Rebuild from the project folder. For local test accounts and sample records run: .venv/Scripts/python -m scripts.seed_showcase'
