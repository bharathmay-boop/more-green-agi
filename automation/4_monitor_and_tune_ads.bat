@echo off
title More Green — Monitor + Tune Ads
cd /d "%~dp0"
echo.
echo =========================================
echo  More Green Studio
echo  Step 4: Monitor + Tune Ad Campaigns
echo =========================================
echo.

echo [1/2] Fetching ad insights...
python main.py monitor-ads
if errorlevel 1 ( echo ERROR: Monitor failed. Check Meta token and ad account ID. & pause & exit /b 1 )

echo.
echo [2/2] Applying optimisation rules...
python main.py tune-ads --apply
if errorlevel 1 ( echo ERROR: Tune failed. & pause & exit /b 1 )

echo.
echo =========================================
echo  Done. Low CTR ads paused, winners
echo  scaled. Check logs/ for details.
echo =========================================
echo.
pause
