@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Flask Database Migrator
set "FLASK_APP=app.py"

:: Prefer the bundled Python; fall back to python on PATH
if exist "python313\python.exe" (
    set "PYTHON_EXE=python313\python.exe"
) else (
    set "PYTHON_EXE=python"
)

echo ============================================
echo      DATABASE MIGRATION TOOL
echo ============================================

:: Ensure the migrations folder exists
if not exist "migrations" (
    echo [!] Migrations folder not found.
    echo [*] Initializing migrations...
    "%PYTHON_EXE%" -m flask db init || goto :error
    echo [+] Initialization complete.
) else (
    echo [v] Migrations folder exists.
)

:: Detect changes and create a migration
:: (flask returns 0 when there are no changes, so only a real error stops here)
echo [*] Checking for database changes...
"%PYTHON_EXE%" -m flask db migrate -m "auto migration %DATE% %TIME%"
if errorlevel 1 (
    echo [!] Migrate failed. Make sure PostgreSQL is running. Skipping upgrade.
    goto :error
)

:: Apply the changes to the database
echo [*] Applying changes to database ^(Upgrade^)...
"%PYTHON_EXE%" -m flask db upgrade
if errorlevel 1 goto :error

echo ============================================
echo   SUCCESS: Database is now up to date!
echo ============================================
pause & exit /b 0

:error
echo ============================================
echo   ERROR: Migration/upgrade failed. Check logs.
echo ============================================
pause & exit /b 1
