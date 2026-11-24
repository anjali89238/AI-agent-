@echo off
cd /d "%~dp0"

echo ============================================
echo   EstateBot - Database Real Estate Bot
echo ============================================

if not exist "venv\Scripts\python.exe" (
  echo Creating virtual environment...
  python -m venv venv
  if errorlevel 1 goto :error
  echo Installing dependencies...
  "venv\Scripts\python.exe" -m pip install --upgrade pip
  "venv\Scripts\python.exe" -m pip install -r requirements.txt
  if errorlevel 1 goto :error
)

echo.
echo Starting server at http://127.0.0.1:8000
echo Keep this window open while using the bot. Press Ctrl+C to stop.
echo.
"venv\Scripts\python.exe" run.py
goto :end

:error
echo.
echo Something went wrong. Make sure Python 3.10+ is installed and on PATH.

:end
echo.
pause
