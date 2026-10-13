@echo off
setlocal
cd /d "%~dp0"

echo Stopping the hidden monitor loop...
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command "$targets = Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'wscript.exe' -and $_.ProcessId -ne $PID -and $_.CommandLine -like '*run_monitor_loop_hidden.vbs*' }; if ($targets) { $targets | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }; Write-Host ('Stopped ' + @($targets).Count + ' hidden monitor loop.') } else { Write-Host 'The hidden monitor loop is not running.' }"

echo.
echo Note: a check that is running right now may take a few more seconds to finish.
echo The Windows scheduled task is not affected by this.
echo.
pause
endlocal
