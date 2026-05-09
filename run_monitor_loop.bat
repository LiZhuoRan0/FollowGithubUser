@echo off
setlocal
cd /d "%~dp0"

echo GitHub Activity Email QQ monitor loop
echo Press Ctrl+C to stop.
echo.

:loop
call run_once.bat
echo.
echo Waiting 3 hours before next check...
timeout /t 10800 /nobreak
goto loop
