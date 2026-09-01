@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Load Fixtures
set "FLASK_APP=app.py"

:: Prefer the bundled Python; fall back to python on PATH
if exist "python313\python.exe" (
    set "PYTHON_EXE=python313\python.exe"
) else (
    set "PYTHON_EXE=python"
)

echo [*] Loading fixtures...
"%PYTHON_EXE%" -m flask seed
if errorlevel 1 (
    echo [!] Fixture load failed. Is PostgreSQL running?
) else (
    echo [+] Fixtures loaded.
)

pause
