@echo off
cd /d "%~dp0"
cls

:: Prefer the bundled Python Scripts; fall back to PATH
if exist "python313\Scripts\black.exe" (
    set "BLACK_EXE=python313\Scripts\black.exe"
) else (
    set "BLACK_EXE=black"
)
if exist "python313\Scripts\flake8.exe" (
    set "FLAKE8_EXE=python313\Scripts\flake8.exe"
) else (
    set "FLAKE8_EXE=flake8"
)

echo Running Black Formatter...
"%BLACK_EXE%" . --exclude "(pgsql|python313|dist)"

echo.
echo Running Flake8 Linter...
"%FLAKE8_EXE%" . --exclude=pgsql,python313,dist --max-line-length=150 --extend-ignore=E203

echo.
@REM pause
