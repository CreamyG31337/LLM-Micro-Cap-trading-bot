@echo off
REM Activate Virtual Environment Script
REM Always run this before executing any Python scripts in this project


echo Activating virtual environment...
call ..\venv\Scripts\activate.bat
echo Virtual environment activated!
echo.
echo You can now run Python scripts safely.
echo Example: python trading_script.py --data-dir test_data
