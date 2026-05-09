@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo Virtual environment not found. Please run setup_venv.bat first.
  exit /b 1
)

".venv\Scripts\python.exe" github_activity_email.py
exit /b %errorlevel%
