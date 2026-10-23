# Universal Telegram Bot: AI Chat, Instagram & YouTube Video Downloader 🎬🤖

Ushbu bot ko'p tarmoqli imkoniyatlarga va to'liq **Admin Panel** tizimiga ega:
1. 👑 **Admin Boshqaruv Paneli:** Foydalanuvchilar soni, kimlar ishlatayotgani, yangi a'zolar xabarnomalari, statistika va barchaga xabar tarqatish.
2. 🤖 **AI Chat Bo'limi:** Sun'iy intellekt (ChatGPT/Gemini AI) bilan istalgan savol-javoblar va erkin suhbat.
3. 📷 **Instagram Yuklovchi:** Reels, Postlar va videolarni to'liq sifatda yuklab berish.
4. 🔴 **YouTube Yuklovchi:** YouTube Shorts va videolarni yuklab berish.
5. 🔘 **Dumaloq Video (Video Note):** To'rtburchak/vertikal videolarni 1:1 kvadrat dumaloq video xabarga aylantirish.

---

## 👑 Admin Panel Imkoniyatlari

Botda quyidagi admin funksiyalari mavjud:
- 📊 **Jonli Statistika:** Jami a'zolar, bugun faol bo'lganlar, bugun qo'shilganlar, 7 kunlik/30 kunlik faollar, jami yuklashlar soni.
- 🔔 **Real-vaqt Xabarnomalari:** Botga yangi foydalanuvchi kirgan zahoti adminga uning ismi, ID raqami va @username'i haqida darhol xabar keladi. (Menyuda bitta tugma bilan yoqish/o'chirish mumkin).
- 👥 **Foydalanuvchilar Ro'yxati:** Oxirgi faol bo'lganlar ro'yxati (sahifalab ko'rish, har birining oxirgi bajargan amali va faollik vaqti).
- 🔍 **Qidiruv Tizimi:** Foydalanuvchini Telegram ID raqami, @username yoki ismi orqali bir zumda topish.
- ✉️ **Shaxsiy Xabar:** Alohida istalgan foydalanuvchiga bot nomidan to'g'ridan-to'g'ri xabar yozish.
- 🚫 **Bloklash (Ban):** Qoidabuzar yoki ortiqcha yuklama beruvchi foydalanuvchini botdan bloklash yoki qayta bandan chiqarish.
- 📢 **Ommaviy Xabar Tarqatish (Broadcast):** Barcha foydalanuvchilarga matn, rasm, video yoki post yuborish (yetkazilganlar va bloklaganlar statistikasi bilan).
- 📥 **Bazani Yuklash (.CSV):** Barcha foydalanuvchilar to'liq bazasini Microsoft Excel uchun qulay `.csv` fayl formatida admin chatiga yuklab olish.

### 🔑 Adminni sozlash:
1. Botga kiring va `/myid` komandasini yuboring. Bot sizga Telegram ID raqamingizni chiqarib beradi.
2. `.env` faylini oching va `ADMIN_ID=` qatoriga o'z ID raqamingizni yozing:
   ```env
   ADMIN_ID=123456789
   ```
   *(Bir nechta admin qo'shish uchun vergul bilan yozing: `ADMIN_ID=123456789,987654321`)*
3. Botni ishga tushiring yoki qayta yurgizing.
4. Botda `/admin` komandasini yuboring yoki menyudagi **«⚙️ Admin Panel»** tugmasini bosing!

---

## 🛠 Texnologiyalar
- **Python 3.10+**
- **aiogram 3.x** — zamonaviy asinxron Telegram Bot freymvorki (FSM holatlari va Middleware bilan)
- **SQLite3** — ishonchli va yengil ma'lumotlar bazasi (foydalanuvchilar va sozlamalar)
- **Google Gemini API / g4f** — Sun'iy intellekt (AI) chat modeli
- **yt-dlp** — Instagram va YouTube platformalaridan mediani yuklab olish
- **imageio-ffmpeg** — videolarni dumaloq formatga qirqish uchun
- **python-dotenv** — maxfiy sozlamalar (.env)

---

## 🛠 O'rnatish va Ishga tushirish

### 1. Kutubxonalarni o'rnatish
```bash
python -m pip install -r requirements.txt
```

### 2. Sozlamalarni kiritish (.env fayli)
`.env` faylini quyidagicha to'ldiring:
```env
BOT_TOKEN=YOUR_TELEGRAM_BOT_TOKEN
GEMINI_API_KEY=YOUR_GEMINI_API_KEY
ADMIN_ID=SIZNING_TELEGRAM_ID
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
4. **Environment Variables** bo'limiga qo'shing:
   - `BOT_TOKEN`
   - `GEMINI_API_KEY`
   - `ADMIN_ID`
5. **Deploy Web Service** tugmasini bosing!
6. Render bergan web havolani [UptimeRobot.com](https://uptimerobot.com) saytida har 5 daqiqada tekshiradigan qilib bepul qo'shib qo'ying.

---

### 2-variant: VPS Server (Ubuntu)
Ubuntu VPS serverda papka ichida bitta buyruqni bajaring:
```bash
chmod +x deploy_vps.sh && ./deploy_vps.sh
```
Ushbu skript avtomatik tarzda `systemd` servisini yaratadi va bot serverda 24/7 to'xtovsiz ishlaydi!
