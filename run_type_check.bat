@echo off
echo Running Type Checks...
.\venv\Scripts\mypy web_dashboard/streamlit_utils.py --explicit-package-bases
echo.
echo Check complete.
pause
