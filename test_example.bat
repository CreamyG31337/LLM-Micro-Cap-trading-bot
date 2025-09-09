@echo off
REM Example script showing how to use test vs production data


echo ========================================
echo LLM Micro-Cap Trading Bot - Test Example
echo ========================================
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
