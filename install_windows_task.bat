@echo off
setlocal
cd /d "%~dp0"

set TASK_NAME=GitHubActivityEmailQQ
set TASK_COMMAND=%~dp0run_once.bat

echo Creating Windows Scheduled Task: %TASK_NAME%
echo It will run every 3 hours.
echo.

schtasks /Create /TN "%TASK_NAME%" /TR "\"%TASK_COMMAND%\"" /SC MINUTE /MO 180 /F

if errorlevel 1 (
  echo.
  echo Failed to create scheduled task.
  echo Try running this file as Administrator, or open Task Scheduler manually.
  pause
  exit /b 1
)

echo.
echo Scheduled task created.
echo You can check it in Windows Task Scheduler.
echo.
pause
endlocal
