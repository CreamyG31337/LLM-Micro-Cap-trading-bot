@echo off
REM Windows batch file to run the LLM Micro-Cap Trading Bot
REM This script automatically activates the virtual environment and runs the master menu

echo.
echo ========================================
echo LLM Micro-Cap Trading Bot - Launcher
echo ========================================
echo.

REM Check if virtual environment exists
if not exist "venv\Scripts\python.exe" (
    echo ERROR: Virtual environment not found!
    echo.
    echo Please create the virtual environment first:
    echo   python -m venv venv
    echo   venv\Scripts\activate
    echo   pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

REM Run the master script using the virtual environment
echo Starting the trading bot menu system...
echo.
venv\Scripts\python.exe run.py

echo.
echo Trading bot session ended.
pause
