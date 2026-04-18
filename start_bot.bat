@echo off
cd /d "%~dp0"
echo ================================
echo   SH_CV Bot - Starting...
echo ================================
echo.
python tools/telegram_bot.py
echo.
echo Bot stopped. Press any key to close.
pause
