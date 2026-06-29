@echo off
cd /d "%~dp0"
echo ==================================================
echo  Window Border Tool - Initial Setup / Setup and Run
echo ==================================================
echo Installing required libraries (PySide6, pywin32)...
echo It may take a minute for the first run. Please wait.
echo.

python -m pip install --upgrade pip
pip install PySide6 pywin32 psutil

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Installation failed.
    echo Please check your internet connection.
    pause
    exit /b
)

echo.
echo [SUCCESS] Ready! Starting the tool...
python main.py
