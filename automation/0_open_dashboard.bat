@echo off
title More Green — Dashboard
cd /d "%~dp0"
echo.
echo =========================================
echo  More Green Studio — Dashboard
echo  Opening at http://localhost:8501
echo =========================================
echo.
echo Press Ctrl+C to stop the dashboard.
echo.
python main.py dashboard
pause
