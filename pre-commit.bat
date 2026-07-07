@echo off
cls

echo Running Black Formatter...
call .\python313\Scripts\black.exe . --exclude "(pgsql|python313|dist)"

echo.
echo Running Flake8 Linter...
call .\python313\Scripts\flake8.exe . --exclude=pgsql,python313,dist --max-line-length=150 --extend-ignore=E203

echo.
@REM pause