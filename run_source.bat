@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
    py -3 src\weather_server.py
) else (
    python src\weather_server.py
)
