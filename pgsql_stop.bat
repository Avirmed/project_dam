@echo off
chcp 65001 >nul
set "DATA_DIR=%~dp0pgsql\data"
set "PG_BIN=%~dp0pgsql\bin"

title 🛑 Stopping Postgres...
cls
echo ==========================================
echo    🔌 SHUTTING DOWN POSTGRES 🔌
echo ==========================================
echo.
echo [⏳] Action: Attempting to stop server safely...

:: 1. Try to stop using pg_ctl
"%PG_BIN%\pg_ctl.exe" -D "%DATA_DIR%" stop -m fast

:: 2. Check if it's still running and force kill if necessary
:: This handles cases where the .pid file is missing but the process is alive
tasklist /FI "IMAGENAME eq postgres.exe" 2>NUL | find /I /N "postgres.exe">NUL
if "%ERRORLEVEL%"=="0" (
    echo [⚠️] Server still detected. Forcing process to terminate...
    taskkill /f /im postgres.exe /t >nul 2>&1
)

echo.
echo ✅ ONLINE: Server stopped.
timeout /t 2
exit