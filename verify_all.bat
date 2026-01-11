@echo off
echo ==========================================
echo      LLM Trading Bot - Verification
echo ==========================================
echo.

echo [1/2] Running Backend Tests (Flask)...
call .\web_dashboard\venv\Scripts\python.exe -m pytest tests/test_flask_routes.py
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Backend tests FAILED
    pause
    exit /b %ERRORLEVEL%
) else (
    echo ✅ Backend tests PASSED
)

echo.
echo [2/2] Running Frontend Tests (TypeScript)...
cd web_dashboard
call npm test
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Frontend tests FAILED
    cd ..
    pause
    exit /b %ERRORLEVEL%
) else (
    echo ✅ Frontend tests PASSED
)
cd ..

echo.
echo === Running Static Asset Verification ===
.\web_dashboard\venv\Scripts\python.exe web_dashboard\verify_assets.py
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Static Asset Verification failed!
    exit /b %ERRORLEVEL%
)

echo.
echo ===================================================
echo   ALL CHECKS PASSED SUCCESSFULLY!
echo ===================================================
pause
