@echo off
setlocal

set TASK_NAME=GitHubActivityEmailQQ

echo Removing Windows Scheduled Task: %TASK_NAME%
schtasks /Delete /TN "%TASK_NAME%" /F

if errorlevel 1 (
  echo.
  echo Failed to remove scheduled task, or it did not exist.
  pause
  exit /b 1
)

echo.
echo Scheduled task removed.
echo.
pause
endlocal
