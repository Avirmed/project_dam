@echo off
cd /d "%~dp0"
cls

:: Prefer the bundled Python; fall back to python on PATH
if exist "python313\python.exe" (
    set "PYTHON_EXE=python313\python.exe"
) else (
    set "PYTHON_EXE=python"
)

:: AI detector: create the ONNX twin of every uploaded model that lacks one
:: (torch-free OpenCV DNN backend). Needs torch; failures are only reported.
echo Checking ONNX models...
"%PYTHON_EXE%" ai\export_onnx.py --missing
echo.

rem :loop
"%PYTHON_EXE%" app.py
rem timeout /t 10
rem goto loop
