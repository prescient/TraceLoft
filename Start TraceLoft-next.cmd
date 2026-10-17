@echo off
rem Start the TraceLoft-next test copy (its own database, web port 8775) and open it.
cd /d "%~dp0"
".venv\Scripts\python.exe" -B launch_next.py
if errorlevel 1 pause
