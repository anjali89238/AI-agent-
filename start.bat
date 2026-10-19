@echo off
cd /d "%~dp0"
echo Starting AI Agent at http://127.0.0.1:8000
echo Press Ctrl+C to stop.
".venv\Scripts\python.exe" run.py
pause