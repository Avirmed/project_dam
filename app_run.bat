@echo off
cd /d "%~dp0"
cls

:: Prefer the bundled Python; fall back to python on PATH
if exist "python313\python.exe" (
    set "PYTHON_EXE=python313\python.exe"
) else (
    set "PYTHON_EXE=python"
)

rem :loop
"%PYTHON_EXE%" app.py
rem timeout /t 10
rem goto loop
