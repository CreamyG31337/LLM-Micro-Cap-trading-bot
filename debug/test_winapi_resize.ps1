# ==========================================================
# APPLICATION INITIALIZATION: SET WINDOW SIZE
# This code should run at the very beginning of your script.
# ==========================================================
Add-Type @"
    using System;
    using System.Runtime.InteropServices;
    public class WinAPI {
        [DllImport("user32.dll", SetLastError=true)]
        public static extern bool MoveWindow(IntPtr hWnd, int X, int Y, int nWidth, int nHeight, bool bRepaint);
        [DllImport("kernel32.dll")]
        public static extern IntPtr GetConsoleWindow();
    }
"@

# Get the handle for the current terminal window
Write-Host "Getting console window handle..." -ForegroundColor Yellow
$consoleHandle = [WinAPI]::GetConsoleWindow()
Write-Host "Console handle: $consoleHandle" -ForegroundColor Yellow

# Set your app's required pixel dimensions (width, height).
# Optimized for 1920x1080 screen - using most of the width
$appWidth = 1600
$appHeight = 800

Write-Host "Attempting to resize window to ${appWidth}x${appHeight} pixels..." -ForegroundColor Yellow

# Call the Windows API to resize the window.
# The 0, 0 for X/Y means the window's top-left corner won't move.
try {
    $result = [WinAPI]::MoveWindow($consoleHandle, 0, 0, $appWidth, $appHeight, $true)
    if ($result) {
        Write-Host "✅ Window resize successful!" -ForegroundColor Green
    } else {
        Write-Host "❌ Window resize failed!" -ForegroundColor Red
        $errorCode = [System.Runtime.InteropServices.Marshal]::GetLastWin32Error()
        Write-Host "Error code: $errorCode" -ForegroundColor Red
    }
} catch {
    Write-Host "❌ Exception during window resize: $($_.Exception.Message)" -ForegroundColor Red
}

Clear-Host
# ==========================================================
# END INITIALIZATION
# ==========================================================

Write-Host "Testing Windows API terminal resizing..." -ForegroundColor Yellow
Write-Host "The window has been automatically resized for the best experience." -ForegroundColor Green
Write-Host ""

Write-Host "COLUMN MEASUREMENT GRID (should show 150+ columns):" -ForegroundColor Cyan
Write-Host ""

# Simple measurement: show exactly 150 characters with clear markers
$line1 = "123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890"
Write-Host $line1 -ForegroundColor White

$line2 = "         10        20        30        40        50        60        70        80        90       100       110       120       130       140       150"
Write-Host $line2 -ForegroundColor Yellow

Write-Host ""
Write-Host "Count the '1234567890' pattern above - should be exactly 15 repetitions = 150 characters" -ForegroundColor Green
Write-Host ""
Write-Host "If you can see the full grid above - 150 characters - Windows API resizing worked!" -ForegroundColor Green
Write-Host "Press any key to continue..." -ForegroundColor Cyan
$null = $Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown')
