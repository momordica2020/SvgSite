@echo off
cd /d "%~dp0"
python app.py
if errorlevel 1 (
    echo.
    echo 启动失败，请确保已安�?Python 3.x
    pause
)