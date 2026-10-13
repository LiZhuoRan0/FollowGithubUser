@echo off
setlocal
cd /d "%~dp0"

echo === Scheduled task GitHubActivityEmailQQ ===
schtasks /Query /TN "GitHubActivityEmailQQ" /FO LIST /V 2>nul | findstr /B /C:"Status" /C:"Last Run Time" /C:"Last Result" /C:"Next Run Time" /C:"Task To Run"

echo.
echo === Last lines of data\monitor.log ===
powershell -NoProfile -Command "if (Test-Path 'data\monitor.log') { Get-Content 'data\monitor.log' -Tail 15 } else { Write-Host 'No log file yet.' }"

echo.
echo === Launcher errors (only exists if something went wrong) ===
powershell -NoProfile -Command "if (Test-Path 'data\hidden_run.log') { Get-Content 'data\hidden_run.log' -Tail 10 } else { Write-Host 'None.' }"

echo.
pause
endlocal
