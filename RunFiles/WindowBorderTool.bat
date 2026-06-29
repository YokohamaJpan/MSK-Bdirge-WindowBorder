@echo off
cd /d "%~dp0"
set DEBUG_MODE=1
set PY_ARGS=
if "%DEBUG_MODE%"=="1" set PY_ARGS=--debug
if "%1"=="--debug" set PY_ARGS=--debug
if "%1"=="debug" set PY_ARGS=--debug
echo Starting Window Border Tool...
python main.py %PY_ARGS%
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] The application terminated unexpectedly.
)
pause
