@echo off
cd /d "%~dp0"
py -3.12 -m venv .venv
if errorlevel 1 goto fail
".venv\Scripts\python.exe" -m pip install -r requirements-web.txt
if errorlevel 1 goto fail
exit /b 0
:fail
pause
exit /b 1
