@echo off
cd /d "%~dp0"
".venv\Scripts\python.exe" -B launch_web.py --lan --remote-input
if errorlevel 1 pause
