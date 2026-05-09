# start.ps1 — launches backend and frontend in separate windows
# Run from the project root: .\start.ps1

$root = Split-Path -Parent $MyInvocation.MyCommand.Path

# Backend
Start-Process powershell -ArgumentList "-NoExit", "-Command", @"
  Set-Location '$root\backend'
  Write-Host '=== SHL Backend ===' -ForegroundColor Cyan
  if (-not (Test-Path '.venv')) {
    python -m venv .venv
  }
  .venv\Scripts\Activate.ps1
  pip install -r requirements.txt -q
  uvicorn main:app --reload --port 8000
"@

# Small delay so backend starts first
Start-Sleep 2

# Frontend
Start-Process powershell -ArgumentList "-NoExit", "-Command", @"
  Set-Location '$root\frontend'
  Write-Host '=== SHL Frontend ===' -ForegroundColor Green
  if (-not (Test-Path 'node_modules')) {
    npm install
  }
  npm run dev
"@

Write-Host ""
Write-Host "Starting SHL Assessment Advisor..." -ForegroundColor Yellow
Write-Host "  Backend  -> http://localhost:8000" -ForegroundColor Cyan
Write-Host "  Frontend -> http://localhost:3000" -ForegroundColor Green
Write-Host ""
Write-Host "Press Ctrl+C in each window to stop." -ForegroundColor Gray
