@echo off
cd /d "%~dp0"

:: Prefer the bundled Python; fall back to python on PATH
if exist "python313\python.exe" (
    set "PYTHON_EXE=python313\python.exe"
) else (
    set "PYTHON_EXE=python"
)

"%PYTHON_EXE%" generate_init.py
if errorlevel 1 echo [!] generate_init.py failed.

pause
