@echo off
title More Green — Sync + Generate Prompts
cd /d "%~dp0"
echo.
echo =========================================
echo  More Green Studio
echo  Step 1: Sync Sheets + Generate Prompts
echo =========================================
echo.

echo [1/2] Syncing from Google Sheets...
python main.py sync-sheets
if errorlevel 1 ( echo ERROR: Sync failed. Check your Google Sheets credentials. & pause & exit /b 1 )

echo.
echo [2/2] Generating prompts with Claude...
python main.py generate-prompts
if errorlevel 1 ( echo ERROR: Prompt generation failed. & pause & exit /b 1 )

echo.
echo =========================================
echo  Done. Open the dashboard to review
echo  and approve prompts before generating
echo  creatives.
echo =========================================
echo.
pause
