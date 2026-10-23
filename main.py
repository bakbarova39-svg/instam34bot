import os
import sys
import uuid
import logging
from dotenv import load_dotenv

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message,
    FSInputFile,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
    ReplyKeyboardMarkup,
    KeyboardButton
)
from aiogram.enums import ChatAction

from downloader import (
    extract_media_url,
    download_video,
    convert_to_round_video,
    cleanup_file,
    DOWNLOAD_DIR
)
from ai_service import ask_ai, reset_chat

# Muhit o'zgaruvchilarini yuklash
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN or BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
    print("XATOLIK: .env faylida BOT_TOKEN ko'rsatilmagan!")
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

dp = Dispatcher()


# Foydalanuvchi holatlari (FSM)
class UserStates(StatesGroup):
    in_ai_chat = State()


# Asosiy menyu klaviaturasi
def get_main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🤖 AI Chat Bo'limi")],
            [KeyboardButton(text="📥 Video Yuklash"), KeyboardButton(text="🔘 Dumaloq Video")]
        ],
        resize_keyboard=True
    )


# AI Chat bo'limi klaviaturasi
def get_ai_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔄 Yangi suhbat boshlash")],
            [KeyboardButton(text="🔙 Asosiy menyuga qaytish")]
        ],
        resize_keyboard=True
    )


# Yuklangan video tagidagi inline tugma
def get_round_button_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔘 Dumaloq video qilish (Video Note)",
                    callback_data="make_round"
                )
            ]
        ]
    )


@dp.message(CommandStart())
@dp.message(Command("menu"))
async def command_start_handler(message: Message, state: FSMContext) -> None:
    """/start va /menu komandalari uchun handler"""
    await state.clear()
    full_name = message.from_user.full_name if message.from_user else "Foydalanuvchi"
    text = (
        f"Assalomu alaykum, {full_name}! 👋\n\n"
        "Men ko'p funksiyali **Yuklovchi, Dumaloq Video va AI Yordamchi** botman.\n\n"
        "**🤖 Asosiy bo'limlar:**\n"
        "• 🤖 **AI Chat Bo'limi:** Sun'iy intellekt bilan istalgan mavzuda suhbatlashish\n"
        "• 📷 **Instagram:** Reels va post videolarini yuklash\n"
        "• 🔴 **YouTube:** Shorts va videolarni yuklash\n"
        "• 🔘 **Dumaloq Video:** Videolarni dumaloq formatga aylantirish\n\n"
        "Quyidagi menyudan kerakli bo'limni tanlang yoki to'g'ridan-to'g'ri havola/video yuboring! 👇"
    )
    await message.answer(text, reply_markup=get_main_keyboard(), parse_mode="Markdown")


@dp.message(Command("help"))
async def command_help_handler(message: Message) -> None:
    """/help komandasi uchun handler"""
    text = (
        "ℹ️ **Botdan foydalanish yo'riqnomasi:**\n\n"
        "🤖 **1. AI Chat:**\n"
        "• «🤖 AI Chat Bo'limi» tugmasini bosing yoki `/ai` komandasini yuboring.\n"
        "• Dasturlash, fan, tarjima yoki ixtiyoriy savollaringizni yozing.\n\n"
        "📥 **2. Video yuklash:**\n"
        "• Instagram yoki YouTube havolasini chatga yuboring.\n\n"
        "🔘 **3. Dumaloq video qilish:**\n"
        "• Botga istalgan video faylni to'g'ridan-to'g'ri yuboring.\n"
        "• Yoki yuklangan video ostidagi «Dumaloq video qilish» tugmasini bosing."
    )
    await message.answer(text, reply_markup=get_main_keyboard(), parse_mode="Markdown")


# --- AI CHAT BO'LIMI BOSHQARUVI ---

@dp.message(F.text == "🤖 AI Chat Bo'limi")
@dp.message(Command("ai"))
async def enter_ai_chat(message: Message, state: FSMContext) -> None:
    """AI Chat bo'limiga kirish"""
    await state.set_state(UserStates.in_ai_chat)
    user_id = message.from_user.id if message.from_user else 0
    reset_chat(user_id)

    text = (
        "🤖 **Sun'iy Intellekt (AI) Chat bo'limiga xush kelibsiz!**\n\n"
        "Menga istalgan savolingizni yozing:\n"
        "• 💡 Dasturlash va IT masalalari\n"
        "• 📚 Ilm-fan, tarix va ta'lim\n"
        "• 🌐 Matnlarni tarjima qilish va tahrirlash\n"
        "• 💬 Maslahatlar va erkin suhbat\n\n"
        "Suhbatni yakunlash uchun pastdagi **«🔙 Asosiy menyuga qaytish»** tugmasini bosing."
    )
    await message.answer(text, reply_markup=get_ai_keyboard(), parse_mode="Markdown")


@dp.message(F.text == "🔙 Asosiy menyuga qaytish")
async def back_to_main_menu(message: Message, state: FSMContext) -> None:
    """AI chatdan chiqib asosiy menyuga qaytish"""
    await state.clear()
    user_id = message.from_user.id if message.from_user else 0
    reset_chat(user_id)
    await message.answer(
        "Siz asosiy menyudasiz. Kerakli xizmatni tanlang:",
        reply_markup=get_main_keyboard()
    )


@dp.message(F.text == "🔄 Yangi suhbat boshlash")
async def clear_ai_history(message: Message, state: FSMContext) -> None:
    """AI bilan yangi suhbat boshlash (tarixni tozalash)"""
    user_id = message.from_user.id if message.from_user else 0
    reset_chat(user_id)
    await message.answer(
        "🧹 **Suhbat tarixi tozalandi!** Yangi mavzudagi savollaringizni berishingiz mumkin.",
        reply_markup=get_ai_keyboard(),
        parse_mode="Markdown"
    )


@dp.message(F.text == "📥 Video Yuklash")
async def video_download_info(message: Message, state: FSMContext) -> None:
    """Video yuklash bo'limi tushuntirishi"""
    await state.clear()
    await message.reply(
        "📥 **Video yuklash uchun:**\n\n"
        "• **Instagram** (Reels, Post) yoki\n"
        "• **YouTube** (Shorts, Video)\n\n"
        "havolasini nusxalab botga yuboring. Bot uni yuklab beradi! 🎬",
        parse_mode="Markdown"
    )


@dp.message(F.text == "🔘 Dumaloq Video")
async def round_video_info(message: Message, state: FSMContext) -> None:
    """Dumaloq video bo'limi tushuntirishi"""
    await state.clear()
    await message.reply(
        "🔘 **Dumaloq video (Video Note) tayyorlash uchun:**\n\n"
        "Telefoningiz galereyasidan yoki boshqa chatdan istalgan **video faylni** "
        "botga to'g'ridan-to'g'ri yuboring. Bot uni 1:1 formatda dumaloq qilib beradi! 🎥",
        parse_mode="Markdown"
    )


# --- MEDIANI YUKLAB YUBORISH UMUMIY FUNKSIYASI ---
async def download_and_send_media(message: Message, bot: Bot, media_info: tuple) -> None:
    """Instagram va YouTube videolarini yuklab foydalanuvchiga yuborish"""
    platform, media_url = media_info

    icon = "📷" if platform == "Instagram" else "🔴"
    status_msg = await message.reply(
        f"⏳ {icon} **{platform}** videosi aniqlanmoqda va yuklab olinmoqda... Iltimos, kuting.",
        parse_mode="Markdown"
    )

    file_path = None
    try:
        await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.UPLOAD_VIDEO)

        data = await download_video(media_url)
        file_path = data.get("file_path")
        title = data.get("title", "")
        uploader = data.get("uploader", "")
        duration = data.get("duration", 0)
        width = data.get("width")
        height = data.get("height")

        if not file_path or not os.path.exists(file_path):
            raise FileNotFoundError("Yuklangan fayl topilmadi.")

        file_size = os.path.getsize(file_path)
        if file_size > 50 * 1024 * 1024:
            raise ValueError("larger than max-filesize")

        me = await bot.get_me()
        bot_username = me.username or "instam34bot"

        caption_lines = []
        if title:
            caption_lines.append(f"🎬 {title[:800]}")
        if uploader:
            caption_lines.append(f"👤 {uploader}")
        caption_lines.append(f"\n📥 @{bot_username} orqali yuklab olindi")
        caption = "\n".join(caption_lines)

        video_input = FSInputFile(file_path)
        await message.reply_video(
            video=video_input,
            caption=caption,
            duration=int(duration) if duration else None,
            width=width,
            height=height,
            supports_streaming=True,
            reply_markup=get_round_button_keyboard()
        )

        await status_msg.delete()

    except Exception as e:
        logger.error(f"Xatolik yuz berdi ({platform}): {e}", exc_info=True)
        err_str = str(e).lower()

        if "larger than max-filesize" in err_str or "max-filesize" in err_str or "entity too large" in err_str:
            error_text = (
                "⚠️ **Video hajmi juda katta!**\n\n"
                "Telegram botlari orqali faqat **50 MB** gacha bo'lgan videolarni yuborish mumkin.\n"
                "Iltimos, qisqaroq video yoki YouTube Shorts havolasini yuboring."
            )
        elif "private" in err_str or "login" in err_str:
            error_text = (
                "⚠️ **Profil yopiq (shaxsiy)!**\n\n"
                "Ushbu video faqat obunachilar uchun yopiq hisoblanadi. "
                "Faqat ommaviy (ochiq) videolarni yuklab olish mumkin."
            )
        else:
            error_text = (
                f"⚠️ Kechirasiz, {platform} videosini yuklab olishda xatolik yuz berdi.\n\n"
                "Sabablar quyidagilardan biri bo'lishi mumkin:\n"
                "• Video o'chirilgan yoki havola noto'g'ri\n"
                "• Video hajmi 50 MB dan oshib ketgan\n"
                "• Platforma tomonidan vaqtinchalik cheklov qo'yilgan"
            )

        try:
            await status_msg.edit_text(error_text, parse_mode="Markdown")
        except Exception:
            await message.reply(error_text, parse_mode="Markdown")

    finally:
        if file_path:
            cleanup_file(file_path)


# --- AI CHAT BO'LIMIDAGI XABARLARNI QAYTA ISHLASH ---

@dp.message(UserStates.in_ai_chat, F.text)
async def process_ai_chat_message(message: Message, bot: Bot) -> None:
    """Foydalanuvchi AI Chat rejimida yozganda javob berish"""
    user_text = message.text or ""

    # Agar foydalanuvchi AI chat ichida bo'lsa ham video havolasi yuborsa, to'g'ridan-to'g'ri yuklab beramiz
    media_info = extract_media_url(user_text)
    if media_info:
        await download_and_send_media(message, bot, media_info)
        return

    # Telegram "yozmoqda..." holati
    await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

    user_id = message.from_user.id if message.from_user else 0
    ai_response = await ask_ai(user_id, user_text)

    # Telegram xabar limiti (4096 belgi) uchun bo'lib yuborish
    chunk_size = 4000
    for i in range(0, len(ai_response), chunk_size):
        chunk = ai_response[i:i + chunk_size]
        try:
            await message.reply(chunk, parse_mode="Markdown")
        except Exception:
            # Agar markdown formati xato bersa, oddiy matn sifatida yuborish
            await message.reply(chunk)


# --- DUMALOQ VIDEO (VIDEO NOTE) HANDLERLARI ---

@dp.callback_query(F.data == "make_round")
async def handle_make_round_callback(callback: CallbackQuery, bot: Bot) -> None:
    """Video ostidagi 'Dumaloq video qilish' tugmasi bosilganda"""
    msg = callback.message
    if not msg or not msg.video:
        await callback.answer("⚠️ Video topilmadi!", show_alert=True)
        return

    await callback.answer("⏳ Dumaloq video tayyorlanmoqda...")
    status_msg = await msg.reply("⏳ Video dumaloq (Video Note) formatga aylantirilmoqda...")

    unique_id = uuid.uuid4().hex[:8]
    temp_input = os.path.join(DOWNLOAD_DIR, f"in_{unique_id}.mp4")
    temp_round = os.path.join(DOWNLOAD_DIR, f"round_{unique_id}.mp4")

    try:
        await bot.send_chat_action(chat_id=msg.chat.id, action=ChatAction.RECORD_VIDEO_NOTE)
        await bot.download(file=msg.video.file_id, destination=temp_input)
        await convert_to_round_video(temp_input, temp_round)

        round_input = FSInputFile(temp_round)
        await msg.reply_video_note(video_note=round_input, length=480)
        await status_msg.delete()

    except Exception as e:
        logger.error(f"Dumaloq video konvertatsiyasida xatolik: {e}", exc_info=True)
        await status_msg.edit_text("⚠️ Videoni dumaloq formatga o'tkazishda xatolik yuz berdi.")
    finally:
        cleanup_file(temp_input)
        cleanup_file(temp_round)


@dp.message(F.video)
@dp.message(F.document & F.document.mime_type.startswith("video/"))
async def handle_video_upload(message: Message, bot: Bot) -> None:
    """Foydalanuvchi to'g'ridan-to'g'ri video yuborganda uni dumaloq videoga aylantirish"""
    file_id = message.video.file_id if message.video else message.document.file_id
    file_size = (message.video.file_size if message.video else message.document.file_size) or 0

    if file_size > 50 * 1024 * 1024:
        await message.reply("⚠️ Video hajmi 50 MB dan katta. Iltimos, kichikroq video yuboring.")
        return

    status_msg = await message.reply("⏳ Video qabul qilindi. Dumaloq (Video Note) formatga aylantirilmoqda...")

    unique_id = uuid.uuid4().hex[:8]
    temp_input = os.path.join(DOWNLOAD_DIR, f"in_{unique_id}.mp4")
    temp_round = os.path.join(DOWNLOAD_DIR, f"round_{unique_id}.mp4")

    try:
        await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.RECORD_VIDEO_NOTE)
        await bot.download(file=file_id, destination=temp_input)
        await convert_to_round_video(temp_input, temp_round)

        round_input = FSInputFile(temp_round)
        await message.reply_video_note(video_note=round_input, length=480)
        await status_msg.delete()

    except Exception as e:
        logger.error(f"Dumaloq video yaratishda xatolik: {e}", exc_info=True)
        await status_msg.edit_text("⚠️ Videoni dumaloq formatga o'tkazishda xatolik yuz berdi.")
    finally:
        cleanup_file(temp_input)
        cleanup_file(temp_round)


# --- INSTAGRAM VA YOUTUBE HAVOLALARINI YUKLASH HANDLERI ---

@dp.message(F.text)
async def handle_incoming_message(message: Message, bot: Bot) -> None:
    """Foydalanuvchi yuborgan Instagram / YouTube havolalarini qayta ishlash"""
    user_text = message.text or ""
    media_info = extract_media_url(user_text)

    # Agar havola topilmasa
    if not media_info:
        await message.reply(
            "❌ Noma'lum buyruq yoki havola.\n\n"
            "• Sun'iy intellekt bilan suhbatlashish uchun **«🤖 AI Chat Bo'limi»** tugmasini bosing.\n"
            "• Video yuklash uchun **Instagram** yoki **YouTube** havolasini yuboring.\n"
            "• Dumaloq video yaratish uchun video fayl yuboring! 🎬",
            reply_markup=get_main_keyboard(),
            parse_mode="Markdown"
        )
        return

    await download_and_send_media(message, bot, media_info)


async def start_health_check_server(port: int) -> None:
    """Render, Koyeb, Railway kabi bulutli platformalarda 24/7 ishlashi uchun health-check porti"""
    from aiohttp import web
    async def ping_handler(request: web.Request) -> web.Response:
        return web.Response(text="Bot 24/7 ishlash holatida faol! 🚀", status=200)

    app = web.Application()
    app.router.add_get("/", ping_handler)
    app.router.add_get("/health", ping_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"Health-check web server {port}-portda ishga tushdi.")


async def main() -> None:
    port_env = os.getenv("PORT")
    if port_env:
        try:
            await start_health_check_server(int(port_env))
        except Exception as e:
            logger.warning(f"Health-check serverni ishga tushirishda xatolik: {e}")

    bot = Bot(token=BOT_TOKEN)
    logger.info("Bot muvaffaqiyatli ishga tushdi!")

    await bot.delete_webhook(drop_pending_updates=False)
    await dp.start_polling(bot)


if __name__ == "__main__":
    import asyncio
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot to'xtatildi.")
