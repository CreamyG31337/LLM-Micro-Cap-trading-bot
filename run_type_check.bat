@echo off
echo Running Type Checks...
.\venv\Scripts\python -m mypy web_dashboard/streamlit_utils.py
echo.
echo Check complete.
pause
