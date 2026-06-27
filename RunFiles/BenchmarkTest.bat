@echo off
cd /d "%~dp0"
echo Starting Performance Benchmark Test...
python benchmark.py
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] The benchmark test terminated unexpectedly.
)
pause
