@echo off
chcp 65001 > nul
title Render.com ga yangi yangilanishlarni yuklash
echo ========================================================
echo   Telegram Bot - Eng so'nggi yangilanishlarni
echo   GitHub va Render.com ga yuborish skripti...
echo ========================================================
echo.
cd /d "%~dp0"

echo [1/2] GitHub bilan aloqa tekshirilmoqda...
git push -u origin main

if %errorlevel% equ 0 (
    echo.
    echo ========================================================
    echo ✅ MUVAFFAQIYATLI YUKLANDI!
    echo.
    echo Render.com 1-2 daqiqada yangi versiyani (Admin panel, 
    echo SQLite baza, xatoliklar tuzatmasi bilan) avtomatik
    echo qayta quradi va 24/7 rejimda to'xtovsiz ishlatadi!
    echo ========================================================
) else (
    echo.
    echo ========================================================
    echo ⚠️ DIQQAT: GitHub tizimiga kirish talab qilinishi mumkin.
    echo Brauzerda ochilgan oynada 'Authorize' tugmasini bosing
    echo yoki shaxsiy GitHub tokeningizni kiriting.
    echo ========================================================
)

echo.
pause
