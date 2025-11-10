# PowerShell build script for Simple Page Saver Backend

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "  Simple Page Saver Backend - Build Script" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""

# Check if virtual environment exists
if (-not (Test-Path "venv")) {
    Write-Host "[1/5] Creating virtual environment..." -ForegroundColor Yellow
    python -m venv venv
} else {
    Write-Host "[1/5] Virtual environment exists" -ForegroundColor Green
}

# Activate virtual environment
Write-Host "[2/5] Activating virtual environment..." -ForegroundColor Yellow
& "venv\Scripts\Activate.ps1"

# Install/upgrade dependencies
Write-Host "[3/5] Installing dependencies..." -ForegroundColor Yellow
pip install --upgrade pip
pip install -r requirements.txt

# Run build script
Write-Host "[4/5] Building executable..." -ForegroundColor Yellow
python build.py

# Check if build was successful
if (Test-Path "dist\SimplePageSaver.exe") {
    Write-Host "[5/5] Build successful!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Executable created at: dist\SimplePageSaver.exe" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "You can now run the executable to start the GUI." -ForegroundColor Green
} else {
    Write-Host "[5/5] Build failed!" -ForegroundColor Red
    Write-Host "Check the output above for errors." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "==================================================" -ForegroundColor Cyan
