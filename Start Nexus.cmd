@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Python environment is missing. Follow README.md setup first.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" scripts\run_local.py
pause
