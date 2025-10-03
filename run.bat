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
    echo Virtual environment not found. Creating it now...
    echo.
    
    REM Create virtual environment
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment!
        echo Please make sure Python is installed and accessible.
        pause
        exit /b 1
    )
    echo Virtual environment created successfully.
    echo.
    
    REM Install requirements
    echo Installing requirements...
    venv\Scripts\pip.exe install -r requirements.txt
    if errorlevel 1 (
        echo ERROR: Failed to install requirements!
        pause
        exit /b 1
    )
    echo Requirements installed successfully.
    echo.
    echo Setup complete!
    echo.
)

REM Run the master script using the virtual environment
:start
echo Starting the trading bot menu system...
echo.
venv\Scripts\python.exe run.py
set exit_code=%errorlevel%

echo.
if %exit_code%==42 (
    echo Trading bot requested restart...
    echo Restarting in 2 seconds...
    timeout /t 2 /nobreak >nul
    goto start
) else (
    echo Trading bot session ended.
    pause
)
