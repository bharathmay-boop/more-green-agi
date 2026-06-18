@echo off
title More Green — Post Today
cd /d "%~dp0"
echo.
echo =========================================
echo  More Green Studio
echo  Step 3: Post to Instagram + Facebook
echo =========================================
echo.
echo Only posts with creatives_approved=1
echo will go out. All others are skipped.
echo.

python main.py post-organic
if errorlevel 1 ( echo ERROR: Posting failed. Check your Meta token. & pause & exit /b 1 )

echo.
echo =========================================
echo  Done. Check Instagram to confirm.
echo =========================================
echo.
pause
