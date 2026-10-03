@echo off
cd /d "%~dp0"
".venv\Scripts\python.exe" -B launch_web.py --stop
if errorlevel 1 pause
