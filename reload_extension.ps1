# PowerShell script to reload Chrome extension for testing
# This automates the manual reload process

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "  Chrome Extension Reload Script" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""

$extensionPath = Join-Path $PSScriptRoot "extension"

# Check if extension directory exists
if (-not (Test-Path $extensionPath)) {
    Write-Host "ERROR: Extension directory not found at: $extensionPath" -ForegroundColor Red
    exit 1
}

Write-Host "Extension path: $extensionPath" -ForegroundColor Gray
Write-Host ""

# Note: Chrome doesn't provide a command-line way to reload extensions
# The best approach is to use Chrome Remote Debugging Protocol

Write-Host "IMPORTANT: Chrome Extension Reload Process" -ForegroundColor Yellow
Write-Host ""
Write-Host "Unfortunately, Chrome doesn't provide a direct command-line" -ForegroundColor Gray
Write-Host "method to reload extensions automatically." -ForegroundColor Gray
Write-Host ""
Write-Host "Manual Steps Required:" -ForegroundColor Cyan
Write-Host "  1. Open Chrome and go to: chrome://extensions/" -ForegroundColor White
Write-Host "  2. Enable 'Developer mode' (toggle in top right)" -ForegroundColor White
Write-Host "  3. Find 'Simple Page Saver' extension" -ForegroundColor White
Write-Host "  4. Click the circular reload icon" -ForegroundColor White
Write-Host ""
Write-Host "Alternative - Automated Method (Advanced):" -ForegroundColor Cyan
Write-Host "  You can use Chrome Remote Debugging Protocol:" -ForegroundColor White
Write-Host "  1. Start Chrome with: chrome.exe --remote-debugging-port=9222" -ForegroundColor White
Write-Host "  2. Use Chrome DevTools Protocol to reload extension" -ForegroundColor White
Write-Host ""
Write-Host "For now, please reload manually following steps 1-4 above." -ForegroundColor Yellow
Write-Host ""

# Open Chrome extensions page
Write-Host "Opening Chrome extensions page..." -ForegroundColor Green
Start-Process "chrome://extensions/"

Write-Host ""
Write-Host "==================================================" -ForegroundColor Cyan

# Alternative: If user wants to use the automated method via CDP
Write-Host ""
Write-Host "Would you like instructions for setting up automated reload? (Y/N)" -ForegroundColor Cyan
$response = Read-Host

if ($response -eq 'Y' -or $response -eq 'y') {
    Write-Host ""
    Write-Host "Setup for Automated Extension Reload:" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "1. Create a Chrome shortcut with debugging enabled:" -ForegroundColor White
    Write-Host "   Target: ""C:\Program Files\Google\Chrome\Application\chrome.exe"" --remote-debugging-port=9222" -ForegroundColor Gray
    Write-Host ""
    Write-Host "2. Install a Chrome extension reload tool:" -ForegroundColor White
    Write-Host "   - 'Extensions Reloader' from Chrome Web Store" -ForegroundColor Gray
    Write-Host "   - Or use CLI tool like 'chrome-ext-reload'" -ForegroundColor Gray
    Write-Host ""
    Write-Host "3. For development, consider using web-ext (for Firefox):" -ForegroundColor White
    Write-Host "   npm install --global web-ext" -ForegroundColor Gray
    Write-Host "   web-ext run (for Firefox auto-reload)" -ForegroundColor Gray
    Write-Host ""
}

Write-Host "Press any key to exit..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
