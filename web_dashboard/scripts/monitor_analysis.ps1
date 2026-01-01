# Quick monitor script for Congress Trades Analysis
# Get the project root (two levels up from scripts folder)
$scriptDir = Split-Path -Parent $PSScriptRoot
$projectRoot = Split-Path -Parent $scriptDir
cd $projectRoot

.\web_dashboard\venv\Scripts\Activate.ps1
python web_dashboard\scripts\monitor_analysis.py

# Pause so window stays open when double-clicked
Write-Host "`nPress any key to exit..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

