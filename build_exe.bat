@echo off
setlocal
cd /d "%~dp0"

echo === HorizonXI Summoner Unlock Tracker - Windows EXE build ===
where py >nul 2>nul
if %errorlevel%==0 (
    set "PY=py -3"
) else (
    where python >nul 2>nul
    if errorlevel 1 (
        echo ERROR: Python 3 was not found.
        echo Install Python 3, then run this file again.
        exit /b 1
    )
    set "PY=python"
)

if not exist ".venv\Scripts\python.exe" (
    echo Creating build virtual environment...
    %PY% -m venv .venv
    if errorlevel 1 exit /b 1
)

call ".venv\Scripts\activate.bat"
if errorlevel 1 exit /b 1

echo Installing/updating build dependencies...
python -m pip install --upgrade pip
if errorlevel 1 exit /b 1
python -m pip install -r requirements-build.txt
if errorlevel 1 exit /b 1

echo Cleaning previous build output...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo Building one-file Windows executable...
python -m PyInstaller --noconfirm --clean HorizonXI_Summoner_Unlock_Tracker.spec
if errorlevel 1 (
    echo.
    echo BUILD FAILED.
    exit /b 1
)

echo.
echo BUILD OK:
echo   dist\HorizonXI_Summoner_Unlock_Tracker.exe
echo.
endlocal
