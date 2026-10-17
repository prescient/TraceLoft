@echo off
rem Stop the TraceLoft-next test copy cleanly; an active session is kept for the next start.
cd /d "%~dp0"
".venv\Scripts\python.exe" -B launch_next.py --stop
if errorlevel 1 pause
