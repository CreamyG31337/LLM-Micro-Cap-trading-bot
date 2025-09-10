@echo off
REM Example script showing how to use test vs production data


echo ========================================
echo LLM Micro-Cap Trading Bot - Test Example
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

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo.
echo Production Mode (default):
echo   python trading_script.py
echo.

echo Test Mode (safe for development):
echo   python trading_script.py --data-dir test_data
echo.

echo Running in TEST MODE with test data...
python trading_script.py --data-dir test_data

echo.
echo Test completed! Your production data in 'my trading' folder is safe.
pause
