@echo off
setlocal
cd /d "%~dp0"

echo Switching the monitor task to "run whether you are logged on or not".
echo Windows will ask for administrator rights.
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process powershell -Verb RunAs -ArgumentList '-NoExit','-NoProfile','-ExecutionPolicy','Bypass','-File','%~dp0enable_run_when_logged_off.ps1'"

if errorlevel 1 (
  echo.
  echo Could not open the administrator window.
  echo Right-click enable_run_when_logged_off.ps1 and run it as Administrator instead.
  pause
  exit /b 1
)

echo.
echo If a User Account Control prompt appeared, approve it to apply the change.
echo The elevated window stays open so you can read the result.
echo Afterwards, check_status.bat shows the new logon type and next run time.
echo.
pause
endlocal
