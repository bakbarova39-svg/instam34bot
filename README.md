# Universal Telegram Bot: AI Chat, Instagram & YouTube Video Downloader 🎬🤖

Ushbu bot ko'p tarmoqli imkoniyatlarga ega:
1. 🤖 **AI Chat Bo'limi:** Sun'iy intellekt (ChatGPT/AI) bilan istalgan savol-javoblar va erkin suhbat
2. 📷 **Instagram Yuklovchi:** Reels, Postlar va videolarni to'liq sifatda yuklab berish
3. 🔴 **YouTube Yuklovchi:** YouTube Shorts va videolarni yuklab berish
4. 🔘 **Dumaloq Video (Video Note):** To'rtburchak/vertikal videolarni 1:1 kvadrat dumaloq video xabarga aylantirish

---

## 🛠 Texnologiyalar
- **Python 3.10+**
- **aiogram 3.x** — zamonaviy asinxron Telegram Bot freymvorki (FSM holatlari bilan)
- **g4f** — Sun'iy intellekt (AI) chat modeli (bepul va tezkor)
- **yt-dlp** — Instagram va YouTube platformalaridan mediani yuklab olish
- **imageio-ffmpeg** — videolarni birlashtirish va dumaloq formatga qirqish uchun
- **python-dotenv** — maxfiy sozlamalar (.env)

---

## 🛠 O'rnatish va Ishga tushirish

### 1. Kutubxonalarni o'rnatish
```bash
python -m pip install -r requirements.txt
```

### 2. Sozlamalarni kiritish (.env fayli)
`.env` faylida Telegram bot tokeni ko'rsatilgan bo'lishi kerak:
```env
BOT_TOKEN=8947731023:AAHPPOUNpLB47CWznnZDrNd7XpqJOR87c-c
```

### 3. Botni kompyuterda ishga tushirish
Windows foydalanuvchilari uchun qulay:
`start_bot.bat` faylini ikki marta bosing (u to'xtab qolsa ham avtomatik qayta yurgizadi).

Yoki terminalda:
```bash
python main.py
```

---

## 🌐 Botni 24/7 ishlatish (Kompyuter o'chiq tursa ham)

### 1-variant: Mutlaqo bepul (Render.com)
1. Ushbu loyihani [GitHub](https://github.com) hisobingizga yuklang (Private yoki Public repository).
2. [Render.com](https://render.com) ga kiring va **New +** -> **Web Service** ni tanlang.
3. GitHub reponi ulang:
   - **Environment:** `Docker` (loyihadagi `Dockerfile` avtomatik tanlanadi)
   - **Plan:** `Free`
4. **Environment Variables** (Muhit o'zgaruvchilari) bo'limiga qo'shing:
   - `BOT_TOKEN` = `sizning_bot_tokeningiz`
   - `GEMINI_API_KEY` = `sizning_gemini_kalitingiz`
5. **Deploy Web Service** tugmasini bosing!
6. *Doimiy uyg'oq turishi uchun:* Render bergan web-sayt havolasini (masalan, `https://bot-xxxx.onrender.com`) [UptimeRobot.com](https://uptimerobot.com) saytida har 5 daqiqada tekshiradigan qilib bepul qo'shib qo'ying.

---

### 2-variant: Eng ishonchli usul (Arzon VPS - Ubuntu)
Oyiga $1-$2 turadigan har qanday Ubuntu VPS server (masalan, Aeza, Beget, Timeweb, Hetzner):
1. Serveringizga fayllarni yuklang.
2. Papka ichida bitta buyruqni bajaring:
```bash
chmod +x deploy_vps.sh && ./deploy_vps.sh
```
Ushbu skript avtomatik tarzda `systemd` servisini yaratadi va kompyuteringiz o'chiq bo'lsa ham bot serverda 24/7 to'xtovsiz ishlaydi!

---

## 💡 Botdan foydalanish:
- **AI Chat:** Menyudagi `[🤖 AI Chat Bo'limi]` tugmasini bosing yoki `/ai` yuboring. AI bilan istalgan mavzuda suhbatlashing.
- **Video yuklash:** Instagram yoki YouTube havolasini chatga tashlang.
- **Dumaloq video:** Botga galereyangizdan ixtiyoriy video yuboring yoki yuklangan video ostidagi «🔘 Dumaloq video qilish» tugmasini bosing.
