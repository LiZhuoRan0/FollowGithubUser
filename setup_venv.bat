@echo off
setlocal
cd /d "%~dp0"

echo [1/4] Checking Python...
python --version
if errorlevel 1 (
  echo.
  echo Python was not found. Please install Python 3.9+ and select "Add python.exe to PATH".
  pause
  exit /b 1
)

echo.
echo [2/4] Creating virtual environment...
python -m venv .venv
if errorlevel 1 (
  echo Failed to create virtual environment.
  pause
  exit /b 1
)

echo.
echo [3/4] Installing dependencies...
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
  echo Failed to install dependencies.
  pause
  exit /b 1
)

echo.
echo [4/4] Creating config.json if needed...
if not exist "config.json" (
  copy "config.example.json" "config.json" >nul
  echo Created config.json. Please edit it before running.
) else (
  echo config.json already exists. Not overwriting.
)

echo.
echo Setup complete.
echo Next steps:
echo   1. Edit config.json
echo   2. Run send_test_email.bat
echo   3. Run run_once_visible.bat
echo   4. Run install_windows_task.bat
echo.
pause
endlocal
