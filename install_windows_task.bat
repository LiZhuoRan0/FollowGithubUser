@echo off
setlocal
cd /d "%~dp0"

echo Registering the background (windowless) Windows Scheduled Task.
echo It will check GitHub every 3 hours without showing any window.
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install_windows_task.ps1"

if errorlevel 1 (
  echo.
  echo Failed to create scheduled task.
  echo Try running this file as Administrator, or open Task Scheduler manually.
  pause
  exit /b 1
)

echo.
echo You can check the task in Windows Task Scheduler.
echo Logs are written to data\monitor.log.
echo.
pause
endlocal
