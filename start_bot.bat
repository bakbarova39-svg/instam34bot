@echo off
chcp 65001 > nul
title Telegram Bot - instatube downloader (Mahalliy sinov)
echo ========================================================
echo   Telegram Bot - Mahalliy (Local) Ishga Tushirish
echo ========================================================
echo.
echo [MUHIM OGOHLANTIRISH]:
echo Agar botingiz Render.com bulutli serverida 24/7 ishlayotgan
echo bo'lsa, ushbu oynani ishga tushirish shart EMAS!
echo Telegram bir vaqtning o'zida ikkita joyda bitta botni
echo ishlatishga yo'l qo'ymaydi (Conflict xatosi yuz beradi).
echo.
echo Kompyuter o'chiq tursa ham bot ishlashi uchun Render.com
echo serveri yetarli va to'liq avtomatik ishlaydi!
echo.
echo Baribir kompyuterda sinov tariqasida ishlatmoqchimisiz?
echo Bot 3 soniyada avtomatik ishga tushadi (to'xtatish uchun oynani yoping)...
timeout /t 3 > nul
echo.
cd /d "%~dp0"

:loop
python main.py
echo.
echo [OGOHLANTIRISH] Bot to'xtadi yoki uzilish yuz berdi.
echo 5 soniyadan so'ng qayta ishga tushiriladi... (To'xtatish uchun Ctrl+C bosing)
timeout /t 5 > nul
goto loop
