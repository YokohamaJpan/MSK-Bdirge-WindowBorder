@echo off
cd /d "%~dp0"
echo Starting Window Border Tool...
python main.py
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] The application terminated unexpectedly.
)
pause
