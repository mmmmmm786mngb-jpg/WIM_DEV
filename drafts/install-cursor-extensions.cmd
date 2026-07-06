@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo Ustanovka rasshirenij Cursor
echo ========================================
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0cursor-extensions-sync.ps1" -Install %*

echo.
echo Nazhmite lyubuyu klavishu dlya vyhoda...
pause >nul
