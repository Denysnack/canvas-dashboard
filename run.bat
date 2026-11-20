@echo off
cd /d "%~dp0"
where py >nul 2>nul && (py dashboard.py & goto end)
where python >nul 2>nul && (python dashboard.py & goto end)
echo Python isn't installed. Get it from https://www.python.org/downloads/ (check "Add python.exe to PATH" during install), then run this again.
:end
pause
