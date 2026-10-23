@echo off
chcp 65001 > nul
title Telegram Bot - Video Yuklovchi Bot (Mahalliy Ishga Tushirish)
echo ========================================================
echo   Telegram Bot - YouTube va Instagram Yuklovchi
echo ========================================================
echo.
echo [INFO] Bot ishga tushirilmoqda...
echo Barcha YouTube videolari va Shorts tezkor yuklanadi.
echo To'xtatish uchun ushbu oynani yoping yoki Ctrl+C bosing.
echo.
cd /d "%~dp0"

:loop
python main.py
echo.
echo [OGOHLANTIRISH] Bot to'xtadi yoki uzilish yuz berdi.
echo 5 soniyadan so'ng qayta ishga tushiriladi...
timeout /t 5 > nul
goto loop
