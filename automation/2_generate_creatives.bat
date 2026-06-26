@echo off
title More Green — Generate Creatives
cd /d "%~dp0"
echo.
echo =========================================
echo  More Green Studio
echo  Step 2: Generate Images / Videos
echo =========================================
echo.
echo Runs FLUX Kontext for image posts and
echo Kling 3.0 for Reels — driven by post_type
echo set in Google Sheets.
echo.
echo Default: strength=0.75, aspect=3:4
echo To override: edit this file and add
echo   --strength 0.65 --aspect-ratio 1:1
echo.

python main.py generate-creatives
if errorlevel 1 ( echo ERROR: Creative generation failed. Check logs/ for details. & pause & exit /b 1 )

echo.
echo [Uploading to Cloudinary...]
python main.py upload-media
if errorlevel 1 ( echo ERROR: Upload failed. & pause & exit /b 1 )

echo.
echo =========================================
echo  Done. Open the dashboard to review
echo  and approve creatives before posting.
echo =========================================
echo.
pause
