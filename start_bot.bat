@echo off
chcp 65001 > nul
title Telegram Bot - instatube downloader
echo ========================================================
echo   Telegram Bot ishga tushirilmoqda...
echo   Bot to'xtab qolmasligi uchun ushbu oynani yopmang!
echo ========================================================
cd /d "%~dp0"

:loop
python main.py
echo.
echo [OGOHLANTIRISH] Bot to'xtadi yoki uzilish yuz berdi.
echo 5 soniyadan so'ng qayta ishga tushiriladi... (To'xtatish uchun Ctrl+C bosing)
timeout /t 5 > nul
goto loop
