@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Run the setup steps in README.md first.
  pause
  exit /b 1
)
if not exist "frontend\dist\index.html" (
  call npm.cmd --prefix frontend run build
  if errorlevel 1 exit /b 1
)
echo CodeMind: http://127.0.0.1:8000
echo Keep this window open. Press Ctrl+C to stop.
".venv\Scripts\python.exe" -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
