@echo off
REM More Green Autonomous Build Engine - Windows Scheduled Task entry point.
REM Invokes the cron-safe resume wrapper via Git Bash. The wrapper holds its own
REM lock (no-ops if a run is already active) and backs off on usage-limit errors,
REM so it is safe to fire every 15 minutes. Output is appended to build/logs/cron.log.
set "REPO=D:\More Green AGI"
set "BASH=C:\Program Files\Git\usr\bin\bash.exe"
cd /d "%REPO%"
"%BASH%" -lc "cd \"$(cygpath -u 'D:\More Green AGI')\" && bash build/resume.sh >> build/logs/cron.log 2>&1"
