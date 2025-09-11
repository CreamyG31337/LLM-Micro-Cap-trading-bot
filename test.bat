@echo off
REM Example script showing how to use test vs production data with the run.py menu

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
echo ========================================
echo TEST MODE - Using test_data folder
echo ========================================
echo.
echo This will run the main menu system but use the test_data folder
echo instead of your production 'my trading' folder.
echo.
echo Your production data in 'my trading' folder is safe!
echo.

REM Set environment variable to use test data
set TEST_DATA_MODE=1

echo Starting main menu in TEST MODE...
echo.
echo NOTE: When you select menu options, they will use test_data folder
echo instead of the production 'my trading' folder.
echo.

python run.py

echo.
echo Test session completed! Your production data in 'my trading' folder is safe.
pause
