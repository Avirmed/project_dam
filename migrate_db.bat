@echo off
chcp 65001 >nul
title Flask Database Migrator
set FLASK_APP=app.py
set PYTHON_EXE=.\python313\python.exe

echo ============================================
echo      DATABASE MIGRATION TOOL
echo ============================================

:: migrations хавтас байгаа эсэхийг шалгах
if not exist "migrations" (
    echo [!] Migrations folder not found.
    echo [*] Initializing migrations...
    call %PYTHON_EXE% -m flask db init
    echo [+] Initialization complete.
) else (
    echo [v] Migrations folder exists.
)

:: Өөрчлөлтийг илрүүлж migrate хийх
echo [*] Checking for database changes...
call %PYTHON_EXE% -m flask db migrate -m "Auto migration %date% %time%"

if %ERRORLEVEL% NEQ 0 (
    echo [!] No changes detected or an error occurred.
) else (
    echo [+] Migration script created successfully.
)

:: Өгөгдлийн сан руу шинэчлэлийг илгээх
echo [*] Applying changes to database (Upgrade)...
call %PYTHON_EXE% -m flask db upgrade

if %ERRORLEVEL% EQU 0 (
    echo ============================================
    echo   SUCCESS: Database is now up to date!
    echo ============================================
) else (
    echo ============================================
    echo   ERROR: Upgrade failed. Check logs.
    echo ============================================
)

pause