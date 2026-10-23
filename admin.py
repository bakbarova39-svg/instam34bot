import os
import sys
import asyncio
import logging
from datetime import datetime
from typing import List, Optional
from dotenv import load_dotenv

load_dotenv()

from aiogram import Router, F, Bot
from aiogram.filters import Command, Filter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    FSInputFile
)
from aiogram.exceptions import TelegramRetryAfter, TelegramForbiddenError, TelegramBadRequest

import database

logger = logging.getLogger(__name__)

admin_router = Router()


def escape_md(text: Optional[str]) -> str:
    """Markdown v1 entity parseri xato bermasligi uchun maxsus belgilarni tozalaydi"""
    if not text:
        return ""
    text_str = str(text)
    for ch in ("_", "*", "`", "[", "]"):
        text_str = text_str.replace(ch, f"\\{ch}")
    return text_str


# --- ADMIN TEKSHIRUVI ---

# Asosiy admin ID raqamlari (barcha sharoitda admin huquqi beriladi)
DEFAULT_ADMIN_IDS = [5671758765, 6026531248]


def get_admin_ids() -> List[int]:
    """ADMIN_ID muhit o'zgaruvchisi, default ro'yxat yoki bazadan adminlar ID ro'yxatini oladi"""
    admins: List[int] = []

    # 1. Birlamchi zaxira adminlar
    for da in DEFAULT_ADMIN_IDS:
        if da not in admins:
            admins.append(da)

    # 2. .env fayli yoki hosting muhit o'zgaruvchilari (ADMIN_ID, ADMINS)
    raw_ids = os.getenv("ADMIN_ID") or os.getenv("ADMINS") or ""
    for item in raw_ids.replace(";", ",").replace(" ", ",").split(","):
        item = item.strip()
        if item.isdigit():
            val = int(item)
            if val not in admins:
                admins.append(val)

    # 3. Ma'lumotlar bazasidagi sozlamalardan
    try:
        db_admin = database._get_setting_sync("admin_id", "")
        for item in db_admin.replace(";", ",").replace(" ", ",").split(","):
            item = item.strip()
            if item.isdigit():
                val = int(item)
                if val not in admins:
                    admins.append(val)
    except Exception:
        pass

    return admins



def is_admin(user_id: Optional[int]) -> bool:
    """Foydalanuvchi admin ekanligini tekshiradi"""
    if not user_id:
        return False
    admins = get_admin_ids()
    return user_id in admins


class IsAdminFilter(Filter):
    """Faqat adminlar uchun mos keluvchi filtr"""
    async def __call__(self, obj: Message | CallbackQuery) -> bool:
        user_id = obj.from_user.id if obj.from_user else None
        return is_admin(user_id)


# --- ADMIN FSM HOLATLARI ---

class AdminStates(StatesGroup):
    waiting_for_search_query = State()
    waiting_for_broadcast_content = State()
    confirming_broadcast = State()
    waiting_for_user_message = State()


# --- KLAVIATURALAR ---

async def get_admin_main_keyboard() -> InlineKeyboardMarkup:
    """Admin panel asosiy inline menyusi"""
    notify_val = await database.get_setting("notify_new_users", "1")
    notify_text = "🔔 Yangi a'zolar xabari: [Yoqilgan ✅]" if notify_val == "1" else "🔕 Yangi a'zolar xabari: [O'chirilgan ❌]"

    keyboard = [
        [
            InlineKeyboardButton(text="📊 Umumiy Statistika", callback_data="admin:stats"),
            InlineKeyboardButton(text="👥 Foydalanuvchilar", callback_data="admin:users:0")
        ],
        [
            InlineKeyboardButton(text="🔍 Qidirish (ID / User)", callback_data="admin:search"),
            InlineKeyboardButton(text="📢 Xabar yuborish", callback_data="admin:broadcast")
        ],
        [
            InlineKeyboardButton(text="👑 Adminlar Ro'yxati", callback_data="admin:list_admins"),
            InlineKeyboardButton(text="📥 Baza yuklash (.csv)", callback_data="admin:export_csv")
        ],
        [
            InlineKeyboardButton(text=notify_text, callback_data="admin:toggle_notify")
        ],
        [
            InlineKeyboardButton(text="❌ Yopish", callback_data="admin:close")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_back_to_admin_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Boshqaruv paneliga qaytish", callback_data="admin:main")]
        ]
    )


# --- ADMINGA REAL-VAQT BILDIRISHNOMA YUBORISH ---

async def notify_admins_about_new_user(bot: Bot, user_data: dict) -> None:
    """Yangi foydalanuvchi botga kirganda adminlarga bildirishnoma yuborish"""
    setting = await database.get_setting("notify_new_users", "1")
    if setting != "1":
        return

    admin_ids = get_admin_ids()
    if not admin_ids:
        return

    user_id = user_data["user_id"]
    # Admin o'zi kirganda o'ziga bildirishnoma yubormaslik
    if user_id in admin_ids:
        return

    first_name = user_data.get("first_name", "") or ""
    username = user_data.get("username")
    uname_str = f"@{username}" if username else "Mavjud emas"
    joined_at = user_data.get("joined_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    stats = await database.get_stats()
    total = stats.get("total_users", 0)

    safe_first = escape_md(first_name)
    safe_uname = escape_md(uname_str)

    text = (
        "🆕 **Yangi foydalanuvchi qo'shildi!**\n\n"
        f"👤 **Ism:** {safe_first}\n"
        f"🆔 **ID:** `{user_id}`\n"
        f"🔗 **Username:** {safe_uname}\n"
        f"📅 **Vaqt:** `{joined_at}`\n"
        f"📊 **Bot a'zolari soni:** {total} ta"
    )

    for admin_id in admin_ids:
        try:
            await bot.send_message(
                chat_id=admin_id,
                text=text,
                parse_mode="Markdown"
            )
        except Exception:
            try:
                plain_text = (
                    "🆕 Yangi foydalanuvchi qo'shildi!\n\n"
                    f"👤 Ism: {first_name}\n"
                    f"🆔 ID: {user_id}\n"
                    f"🔗 Username: {uname_str}\n"
                    f"📅 Vaqt: {joined_at}\n"
                    f"📊 Bot a'zolari soni: {total} ta"
                )
                await bot.send_message(chat_id=admin_id, text=plain_text)
            except Exception as e:
                logger.warning(f"Adminga ({admin_id}) xabarnoma yuborishda xatolik: {e}")


# --- ADMIN KOMANDALARI ---

@admin_router.message(Command("myid"))
@admin_router.message(Command("id"))
async def cmd_my_id(message: Message) -> None:
    """Foydalanuvchining o'z Telegram ID raqamini aniqlash komandasi"""
    user = message.from_user
    user_id = user.id if user else 0
    full_name = user.full_name if user else "Noma'lum"
    username = f"@{user.username}" if (user and user.username) else "Mavjud emas"

    is_user_admin = is_admin(user_id)
    admin_status = "✅ Siz adminsiz" if is_user_admin else "Oddiy foydalanuvchi"

    text = (
        "🆔 **Sizning Telegram profilingiz:**\n\n"
        f"👤 **Ism:** {full_name}\n"
        f"🆔 **Telegram ID:** `{user_id}`\n"
        f"🔗 **Username:** {username}\n"
        f"🔰 **Holat:** {admin_status}\n"
    )

    if is_user_admin:
        text += (
            "\n👑 **Admin boshqaruvi:** Boshqaruv panelini ochish uchun pastdagi "
            "«⚙️ Admin Panel» tugmasini bosing yoki `/admin` buyrug'ini yuboring."
        )
    else:
        text += (
            "\n💡 *Eslatma:* Agar siz bot egasi bo'lsangiz, ushbu ID raqamni `.env` "
            f"faylidagi `ADMIN_ID=` qatoriga qo'shing yoki admin orqali `/setadmin {user_id}` qiling."
        )

    await message.answer(text, parse_mode="Markdown")


@admin_router.message(Command("setadmin"))
async def cmd_set_admin(message: Message) -> None:
    """Yangi admin qo'shish komandasi (faqat mavjud adminlar uchun)"""
    user_id = message.from_user.id if message.from_user else 0
    if not is_admin(user_id):
        await message.answer("⛔ Siz bot admini emassiz!")
        return

    parts = message.text.split() if message.text else []
    if len(parts) < 2 or not parts[1].strip().isdigit():
        await message.answer(
            "ℹ️ Yangi admin qo'shish uchun uning Telegram ID raqamini yuboring:\n\n"
            "Masalan: `/setadmin 6026531248`",
            parse_mode="Markdown"
        )
        return

    new_id = int(parts[1].strip())
    admins = get_admin_ids()
    if new_id in admins:
        await message.answer(f"ℹ️ Ushbu ID (`{new_id}`) allaqachon adminlar ro'yxatida mavjud.", parse_mode="Markdown")
        return

    admins.append(new_id)
    new_admins_str = ",".join(str(a) for a in admins)
    await database.set_setting("admin_id", new_admins_str)

    await message.answer(
        f"✅ Foydalanuvchi `{new_id}` muvaffaqiyatli admin etib tayinlandi!\n"
        f"Jami adminlar soni: {len(admins)} ta.",
        parse_mode="Markdown"
    )


@admin_router.message(Command("deladmin"))
async def cmd_del_admin(message: Message) -> None:
    """Adminlikdan chiqarish komandasi"""
    user_id = message.from_user.id if message.from_user else 0
    if not is_admin(user_id):
        await message.answer("⛔ Siz bot admini emassiz!")
        return

    parts = message.text.split() if message.text else []
    if len(parts) < 2 or not parts[1].strip().isdigit():
        await message.answer("Masalan: `/deladmin 123456789`", parse_mode="Markdown")
        return

    target_id = int(parts[1].strip())
    admins = get_admin_ids()
    if target_id not in admins:
        await message.answer(f"ℹ️ `{target_id}` adminlar ro'yxatida topilmadi.", parse_mode="Markdown")
        return

    admins = [a for a in admins if a != target_id]
    new_admins_str = ",".join(str(a) for a in admins)
    await database.set_setting("admin_id", new_admins_str)

    await message.answer(
        f"✅ `{target_id}` adminlar ro'yxatidan chiqarildi.",
        parse_mode="Markdown"
    )


@admin_router.message(Command("admin"))
@admin_router.message(F.text == "⚙️ Admin Panel")
async def cmd_admin_panel(message: Message, state: FSMContext) -> None:
    """Admin panelni ochish komandasi"""
    user_id = message.from_user.id if message.from_user else 0

    admin_ids = get_admin_ids()
    if not admin_ids:
        # Admin ID hali o'rnatilmagan bo'lsa, qulay yo'riqnoma berish
        await message.answer(
            "⚠️ **Botda Admin ID belgilanmagan!**\n\n"
            f"Sizning Telegram ID raqamingiz: `{user_id}`\n\n"
            "Admin panelga kirish uchun `.env` faylini oching va quyidagi qatorni yozing:\n"
            f"`ADMIN_ID={user_id}`\n\n"
            "So'ngra botni qayta ishga tushiring.",
            parse_mode="Markdown"
        )
        return

    if not is_admin(user_id):
        await message.answer(
            "⛔ **Kechirasiz, ushbu bo'lim faqat bot adminlari uchun mo'ljallangan!**\n\n"
            f"Sizning Telegram ID raqamingiz: `{user_id}`\n"
            "O'zingizni admin qilish uchun uni `.env` faylidagi `ADMIN_ID=` qatoriga qo'shing.",
            parse_mode="Markdown"
        )
        return

    await state.clear()
    kb = await get_admin_main_keyboard()
    await message.answer(
        "👑 **Boshqaruv Paneli (Admin Panel)**\n\n"
        "Xush kelibsiz! Quyidagi menyu orqali bot foydalanuvchilarini kuzatishingiz, "
        "statistikani ko'rishingiz, xabarlar yuborishingiz va bazani yuklab olishingiz mumkin:",
        reply_markup=kb,
        parse_mode="Markdown"
    )


# --- ADMIN INLINE CALLBACKLARI ---

@admin_router.callback_query(IsAdminFilter(), F.data == "admin:main")
async def cb_admin_main(callback: CallbackQuery, state: FSMContext) -> None:
    """Asosiy admin menyusiga qaytish"""
    await state.clear()
    kb = await get_admin_main_keyboard()
    try:
        await callback.message.edit_text(
            "👑 **Boshqaruv Paneli (Admin Panel)**\n\n"
            "Kerakli bo'limni tanlang:",
            reply_markup=kb,
            parse_mode="Markdown"
        )
    except Exception:
        await callback.message.answer(
            "👑 **Boshqaruv Paneli (Admin Panel)**",
            reply_markup=kb,
            parse_mode="Markdown"
        )
    await callback.answer()


@admin_router.callback_query(IsAdminFilter(), F.data == "admin:close")
async def cb_admin_close(callback: CallbackQuery, state: FSMContext) -> None:
    """Admin panelni yopish"""
    await state.clear()
    try:
        await callback.message.delete()
    except Exception:
        await callback.message.edit_text("🔒 Admin panel yopildi.")
    await callback.answer("Admin panel yopildi")


@admin_router.callback_query(IsAdminFilter(), F.data == "admin:stats")
async def cb_admin_stats(callback: CallbackQuery) -> None:
    """Umumiy statistikani ko'rsatish"""
    stats = await database.get_stats()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    text = (
        "📊 **Bot Statistikasi:**\n\n"
        f"👥 **Jami foydalanuvchilar:** {stats['total_users']:,} ta\n"
        f"🟢 **Bugun faol bo'lganlar:** {stats['active_today']:,} ta\n"
        f"🆕 **Bugun qo'shilganlar:** {stats['new_today']:,} ta\n"
        f"📅 **Oxirgi 7 kunda faol:** {stats['active_week']:,} ta\n"
        f"🗓 **Oxirgi 30 kunda faol:** {stats['active_month']:,} ta\n"
        f"⚡ **Jami so'rovlar / amallar:** {stats['total_actions']:,} marta\n"
        f"🚫 **Bloklanganlar:** {stats['banned_users']} ta\n\n"
        f"⏰ *Oxirgi yangilanish:* `{now_str}`"
    )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔄 Yangilash", callback_data="admin:stats"),
                InlineKeyboardButton(text="📥 Bazani yuklash (.csv)", callback_data="admin:export_csv")
            ],
            [
                InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin:main")
            ]
        ]
    )

    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    except Exception as e:
        if "message is not modified" not in str(e).lower():
            try:
                await callback.message.edit_text(text.replace("**", "").replace("`", ""), reply_markup=kb)
            except Exception:
                pass
    await callback.answer("Statistika yangilandi!")


@admin_router.callback_query(IsAdminFilter(), F.data == "admin:list_admins")
async def cb_admin_list_admins(callback: CallbackQuery) -> None:
    """Adminlar ro'yxatini ko'rsatish"""
    admins = get_admin_ids()
    text_lines = ["👑 **Bot Adminlari Ro'yxati:**\n"]
    for idx, aid in enumerate(admins, start=1):
        u = await database.get_user(aid)
        uname = f"@{u['username']}" if (u and u.get("username")) else ""
        fname = u.get("first_name", "") if u else ""
        name_str = f" - {fname} {uname}".strip() if (fname or uname) else ""
        text_lines.append(f"**{idx}.** `{aid}`{name_str}")

    text_lines.append("\n💡 *Yangi admin qo'shish:* `/setadmin <ID>`")
    text_lines.append("💡 *Adminni o'chirish:* `/deladmin <ID>`")

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Yangilash", callback_data="admin:list_admins")],
            [InlineKeyboardButton(text="🔙 Boshqaruv paneli", callback_data="admin:main")]
        ]
    )
    try:
        await callback.message.edit_text("\n".join(text_lines), reply_markup=kb, parse_mode="Markdown")
    except Exception:
        await callback.message.edit_text("\n".join(text_lines).replace("**", "").replace("`", ""), reply_markup=kb)
    await callback.answer()



@admin_router.callback_query(IsAdminFilter(), F.data.startswith("admin:users:"))
async def cb_admin_users(callback: CallbackQuery) -> None:
    """Foydalanuvchilar ro'yxatini sahifalab ko'rish"""
    parts = callback.data.split(":")
    page = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 0
    limit = 8
    offset = page * limit

    users, total = await database.get_users_page(limit=limit, offset=offset)
    total_pages = max(1, (total + limit - 1) // limit)

    if not users:
        text = "👥 Hozircha foydalanuvchilar mavjud emas."
        kb = get_back_to_admin_keyboard()
        await callback.message.edit_text(text, reply_markup=kb)
        await callback.answer()
        return

    text_lines = [
        f"👥 **Foydalanuvchilar ro'yxati** ({page + 1}/{total_pages}-sahifa, jami: {total}):\n"
    ]

    user_buttons = []
    for idx, u in enumerate(users, start=offset + 1):
        uname = escape_md(f"@{u['username']}" if u['username'] else "yo'q")
        fname = escape_md(u['first_name'] or "Noma'lum")
        status_icon = "🚫" if u['is_banned'] else "🟢"
        text_lines.append(
            f"{status_icon} **{idx}. {fname}** ({uname})\n"
            f"   🆔 `{u['user_id']}` | ⚡ {u['usage_count']} marta\n"
            f"   🕒 Faol: `{u['last_active']}` | 🎯 {escape_md(u['last_action'])}\n"
        )
        user_buttons.append(
            InlineKeyboardButton(
                text=f"👤 #{idx} {(u['first_name'] or 'User')[:10]}",
                callback_data=f"admin:uview:{u['user_id']}:{page}"
            )
        )

    # 2 qatordan tugmalar
    keyboard = []
    for i in range(0, len(user_buttons), 2):
        keyboard.append(user_buttons[i:i + 2])

    # Navigatsiya tugmalari
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"admin:users:{page - 1}"))
    nav_row.append(InlineKeyboardButton(text=f"📄 {page + 1}/{total_pages}", callback_data="noop"))
    if page + 1 < total_pages:
        nav_row.append(InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"admin:users:{page + 1}"))

    keyboard.append(nav_row)
    keyboard.append([
        InlineKeyboardButton(text="🔍 Qidirish", callback_data="admin:search"),
        InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin:main")
    ])

    joined_text = "\n".join(text_lines)
    try:
        await callback.message.edit_text(
            joined_text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
            parse_mode="Markdown"
        )
    except Exception:
        await callback.message.edit_text(
            joined_text.replace("**", "").replace("`", "").replace("\\", ""),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
    await callback.answer()


@admin_router.callback_query(IsAdminFilter(), F.data.startswith("admin:uview:"))
async def cb_admin_user_view(callback: CallbackQuery) -> None:
    """Alohida bitta foydalanuvchi tafsilotlari"""
    parts = callback.data.split(":")
    user_id = int(parts[2])
    return_page = parts[3] if len(parts) > 3 else "0"

    u = await database.get_user(user_id)
    if not u:
        await callback.answer("⚠️ Foydalanuvchi topilmadi!", show_alert=True)
        return

    uname = escape_md(f"@{u['username']}" if u['username'] else "Mavjud emas")
    ban_status = "🚫 Bloklangan (Botdan foydalana olmaydi)" if u['is_banned'] else "🟢 Faol (Ruxsat berilgan)"

    text = (
        "👤 **Foydalanuvchi Tafsilotlari:**\n\n"
        f"🆔 **Telegram ID:** `{u['user_id']}`\n"
        f"👤 **Ism:** {escape_md(u['first_name'] or '')}\n"
        f"👥 **Familiya:** {escape_md(u['last_name'] or '')}\n"
        f"🔗 **Username:** {uname}\n"
        f"📅 **Qo'shilgan sana:** `{u['joined_at']}`\n"
        f"⏰ **Oxirgi faollik:** `{u['last_active']}`\n"
        f"🎯 **Oxirgi amal:** {escape_md(u['last_action'])}\n"
        f"⚡ **Foydalanishlar soni:** {u['usage_count']} marta\n"
        f"🔰 **Holati:** {ban_status}"
    )

    ban_btn_text = "✅ Bandan chiqarish" if u['is_banned'] else "🚫 Bloklash (Ban)"
    ban_callback = f"admin:toggle_ban:{u['user_id']}:{return_page}"

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=ban_btn_text, callback_data=ban_callback),
                InlineKeyboardButton(text="✉️ Xabar yozish", callback_data=f"admin:send_pm:{u['user_id']}")
            ],
            [
                InlineKeyboardButton(text="🔙 Ro'yxatga qaytish", callback_data=f"admin:users:{return_page}"),
                InlineKeyboardButton(text="👑 Boshqaruv paneli", callback_data="admin:main")
            ]
        ]
    )

    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    except Exception:
        await callback.message.edit_text(text.replace("**", "").replace("`", "").replace("\\", ""), reply_markup=kb)
    await callback.answer()


@admin_router.callback_query(IsAdminFilter(), F.data.startswith("admin:toggle_ban:"))
async def cb_admin_toggle_ban(callback: CallbackQuery) -> None:
    """Foydalanuvchini bloklash yoki bandan chiqarish"""
    parts = callback.data.split(":")
    user_id = int(parts[2])
    return_page = parts[3] if len(parts) > 3 else "0"

    u = await database.get_user(user_id)
    if not u:
        await callback.answer("Foydalanuvchi topilmadi!", show_alert=True)
        return

    new_ban_state = 0 if u['is_banned'] else 1
    await database.set_ban_status(user_id, new_ban_state)

    status_msg = "Foydalanuvchi bloklandi! 🚫" if new_ban_state else "Foydalanuvchi bandan chiqarildi! ✅"
    await callback.answer(status_msg, show_alert=True)

    # Profil ko'rinishini yangilash
    callback.data = f"admin:uview:{user_id}:{return_page}"
    await cb_admin_user_view(callback)



@admin_router.callback_query(IsAdminFilter(), F.data == "admin:toggle_notify")
async def cb_admin_toggle_notify(callback: CallbackQuery) -> None:
    """Yangi foydalanuvchi haqidagi xabarnomani yoqish/o'chirish"""
    new_val = await database.toggle_setting("notify_new_users")
    msg = "Yangi a'zolar xabarnomasi YOQILDI! 🔔" if new_val == "1" else "Yangi a'zolar xabarnomasi O'CHIRILDI! 🔕"
    await callback.answer(msg, show_alert=True)

    kb = await get_admin_main_keyboard()
    try:
        await callback.message.edit_reply_markup(reply_markup=kb)
    except Exception:
        pass


@admin_router.callback_query(IsAdminFilter(), F.data == "admin:export_csv")
async def cb_admin_export_csv(callback: CallbackQuery, bot: Bot) -> None:
    """Barcha foydalanuvchilar ma'lumotlarini Excel/CSV fayl sifatida yuborish"""
    await callback.answer("⏳ Baza shakllantirilmoqda...")
    now_tag = datetime.now().strftime("%Y%m%d_%H%M%S")
    temp_csv = os.path.join(os.path.dirname(__file__), f"users_export_{now_tag}.csv")

    try:
        total = await database.export_users_csv(temp_csv)
        doc = FSInputFile(temp_csv, filename=f"bot_foydalanuvchilari_{now_tag}.csv")
        await bot.send_document(
            chat_id=callback.from_user.id,
            document=doc,
            caption=(
                f"📊 **Bot foydalanuvchilar bazasi (.CSV)**\n\n"
                f"• Jami qatorlar soni: **{total} ta**\n"
                f"• Ushbu faylni **Microsoft Excel** yoki istalgan jadval dasturida ochishingiz mumkin."
            ),
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"CSV eksportida xatolik: {e}", exc_info=True)
        await callback.message.answer(f"⚠️ Faylni yaratishda xatolik yuz berdi: {e}")
    finally:
        if os.path.exists(temp_csv):
            try:
                os.remove(temp_csv)
            except Exception:
                pass


# --- QIDIRUV FUNKSIYASI ---

@admin_router.callback_query(IsAdminFilter(), F.data == "admin:search")
async def cb_admin_search(callback: CallbackQuery, state: FSMContext) -> None:
    """Foydalanuvchini qidirish bosqichi"""
    await state.set_state(AdminStates.waiting_for_search_query)
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="admin:main")]
        ]
    )
    await callback.message.edit_text(
        "🔍 **Foydalanuvchini qidirish:**\n\n"
        "Foydalanuvchining **Telegram ID** raqamini, **@username**'ini yoki **ismini** yuboring:",
        reply_markup=kb,
        parse_mode="Markdown"
    )
    await callback.answer()


@admin_router.message(IsAdminFilter(), AdminStates.waiting_for_search_query)
async def process_admin_search_query(message: Message, state: FSMContext) -> None:
    """Qidiruv so'rovini qabul qilish va natijalarni chiqarish"""
    query = (message.text or "").strip()
    if not query:
        await message.reply("Iltimos, qidiruv uchun matn yoki ID yuboring.")
        return

    results = await database.search_users(query, limit=10)
    await state.clear()

    if not results:
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="🔍 Qayta qidirish", callback_data="admin:search"),
                    InlineKeyboardButton(text="🔙 Admin menyu", callback_data="admin:main")
                ]
            ]
        )
        await message.reply(
            f"🔍 *«{query}»* bo'yicha hech qanday foydalanuvchi topilmadi.",
            reply_markup=kb,
            parse_mode="Markdown"
        )
        return

    text_lines = [f"🔍 **Qidiruv natijalari («{escape_md(query)}», topildi: {len(results)} ta):**\n"]
    buttons = []

    for idx, u in enumerate(results, start=1):
        uname = escape_md(f"@{u['username']}" if u['username'] else "yo'q")
        fname = escape_md(u['first_name'] or "Noma'lum")
        status_icon = "🚫" if u['is_banned'] else "🟢"
        text_lines.append(
            f"{status_icon} **{idx}. {fname}** ({uname})\n"
            f"   🆔 `{u['user_id']}` | 🕒 `{u['last_active']}`\n"
        )
        buttons.append(
            InlineKeyboardButton(text=f"👤 #{idx} {(u['first_name'] or 'User')[:10]}", callback_data=f"admin:uview:{u['user_id']}:0")
        )

    kb_rows = []
    for i in range(0, len(buttons), 2):
        kb_rows.append(buttons[i:i + 2])

    kb_rows.append([
        InlineKeyboardButton(text="🔍 Yangi qidiruv", callback_data="admin:search"),
        InlineKeyboardButton(text="🔙 Admin menyu", callback_data="admin:main")
    ])

    search_report = "\n".join(text_lines)
    try:
        await message.reply(
            search_report,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows),
            parse_mode="Markdown"
        )
    except Exception:
        await message.reply(
            search_report.replace("**", "").replace("`", "").replace("\\", ""),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows)
        )


# --- BIR FOYDALANUVCHIGA XUSUSIY XABAR YOZISH ---

@admin_router.callback_query(IsAdminFilter(), F.data.startswith("admin:send_pm:"))
async def cb_admin_send_pm_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    """Foydalanuvchiga to'g'ridan-to'g'ri xabar yozishni so'rash"""
    parts = callback.data.split(":")
    user_id = int(parts[2])
    await state.update_data(target_user_id=user_id)
    await state.set_state(AdminStates.waiting_for_user_message)

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"admin:uview:{user_id}:0")]
        ]
    )
    await callback.message.edit_text(
        f"✉️ **ID `{user_id}` ga xabar yuborish:**\n\n"
        "Foydalanuvchiga yubormoqchi bo'lgan xabaringiz matnini yozib yuboring:",
        reply_markup=kb,
        parse_mode="Markdown"
    )
    await callback.answer()


@admin_router.message(IsAdminFilter(), AdminStates.waiting_for_user_message)
async def process_admin_pm_send(message: Message, state: FSMContext, bot: Bot) -> None:
    """Foydalanuvchiga xabarni yetkazish"""
    data = await state.get_data()
    target_user_id = data.get("target_user_id")
    await state.clear()

    if not target_user_id:
        await message.reply("Xatolik: foydalanuvchi ID si topilmadi.")
        return

    text_to_send = (
        "📩 **Bot administratsiyasidan xabar:**\n\n"
        f"{message.text}"
    )

    try:
        await bot.send_message(chat_id=target_user_id, text=text_to_send, parse_mode="Markdown")
        await message.reply(
            f"✅ Xabar muvaffaqiyatli yetkazildi! (ID: `{target_user_id}`)",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="👤 Foydalanuvchi profiliga qaytish", callback_data=f"admin:uview:{target_user_id}:0")]
                ]
            ),
            parse_mode="Markdown"
        )
    except TelegramForbiddenError:
        await message.reply("⚠️ Xabar yuborilmadi: foydalanuvchi botni bloklagan.")
    except Exception as e:
        await message.reply(f"⚠️ Xabar yuborishda xatolik yuz berdi: {e}")


# --- BARCHAGA XABAR YUBORISH (BROADCAST) ---

@admin_router.callback_query(IsAdminFilter(), F.data == "admin:broadcast")
async def cb_admin_broadcast(callback: CallbackQuery, state: FSMContext) -> None:
    """Broadcast boshlash - xabarni qabul qilish holati"""
    await state.set_state(AdminStates.waiting_for_broadcast_content)

    stats = await database.get_stats()
    total = stats.get("total_users", 0)

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="admin:main")]
        ]
    )

    await callback.message.edit_text(
        "📢 **Barcha bot foydalanuvchilariga xabar tarqatish (Broadcast)**\n\n"
        f"Ayni vaqtda faol foydalanuvchilar soni: **{total} ta**\n\n"
        "Yubormoqchi bo'lgan xabaringizni (matn, rasm, video yoki post) chatga yuboring:\n"
        "*(Bekor qilish uchun pastdagi tugmani bosing)*",
        reply_markup=kb,
        parse_mode="Markdown"
    )
    await callback.answer()


@admin_router.message(IsAdminFilter(), AdminStates.waiting_for_broadcast_content)
async def process_broadcast_message_preview(message: Message, state: FSMContext) -> None:
    """Yuboriladigan xabarni saqlab, admindan tasdiqlashni so'rash"""
    await state.update_data(
        broadcast_chat_id=message.chat.id,
        broadcast_message_id=message.message_id
    )
    await state.set_state(AdminStates.confirming_broadcast)

    stats = await database.get_stats()
    total = stats.get("total_users", 0)

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🚀 Ha, hammaga yuborilsin!", callback_data="admin:bcast_confirm"),
                InlineKeyboardButton(text="❌ Bekor qilish", callback_data="admin:bcast_cancel")
            ]
        ]
    )

    await message.reply(
        "⚠️ **Xabarnomani tasdiqlang:**\n\n"
        f"Yuqoridagi xabar barcha **{total} ta** foydalanuvchiga yuboriladi.\n"
        "Haqiqatan ham yuborishni xohlaysizmi?",
        reply_markup=kb,
        parse_mode="Markdown"
    )


@admin_router.callback_query(IsAdminFilter(), F.data == "admin:bcast_cancel")
async def cb_admin_bcast_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    """Broadcastni bekor qilish"""
    await state.clear()
    await callback.message.edit_text("❌ Xabar tarqatish bekor qilindi.")
    kb = await get_admin_main_keyboard()
    await callback.message.answer("👑 **Boshqaruv Paneli (Admin Panel)**", reply_markup=kb, parse_mode="Markdown")
    await callback.answer()


@admin_router.callback_query(IsAdminFilter(), F.data == "admin:bcast_confirm")
async def cb_admin_bcast_confirm(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    """Broadcastni amalga oshirish"""
    data = await state.get_data()
    from_chat_id = data.get("broadcast_chat_id")
    from_message_id = data.get("broadcast_message_id")
    await state.clear()

    if not from_chat_id or not from_message_id:
        await callback.message.edit_text("⚠️ Xatolik: Yuboriladigan xabar topilmadi.")
        await callback.answer()
        return

    user_ids = await database.get_all_broadcast_user_ids()
    total_users = len(user_ids)

    if total_users == 0:
        await callback.message.edit_text("⚠️ Bazada foydalanuvchilar mavjud emas.")
        await callback.answer()
        return

    status_msg = await callback.message.edit_text(
        f"🚀 **Xabar tarqatish boshlandi...**\n\n"
        f"Jami foydalanuvchilar: **{total_users} ta**\n"
        f"Iltimos, kuting...",
        parse_mode="Markdown"
    )

    start_time = datetime.now()
    sent_count = 0
    blocked_count = 0
    failed_count = 0

    # Rate limiting: 25 ta xabar/sekund
    for idx, uid in enumerate(user_ids, start=1):
        try:
            await bot.copy_message(
                chat_id=uid,
                from_chat_id=from_chat_id,
                message_id=from_message_id
            )
            sent_count += 1
        except TelegramRetryAfter as e:
            await asyncio.sleep(e.retry_after)
            try:
                await bot.copy_message(
                    chat_id=uid,
                    from_chat_id=from_chat_id,
                    message_id=from_message_id
                )
                sent_count += 1
            except Exception:
                failed_count += 1
        except TelegramForbiddenError:
            # Foydalanuvchi botni bloklagan
            blocked_count += 1
        except Exception as e:
            logger.debug(f"Broadcast xatosi (user {uid}): {e}")
            failed_count += 1

        # Har 50 ta xabarda statusni yangilash
        if idx % 50 == 0:
            try:
                await status_msg.edit_text(
                    f"🚀 **Xabar tarqatilmoqda...**\n\n"
                    f"• Jarayon: {idx}/{total_users}\n"
                    f"• Yetkazildi: {sent_count}\n"
                    f"• Bloklaganlar: {blocked_count}\n"
                    f"• Xatolar: {failed_count}",
                    parse_mode="Markdown"
                )
            except Exception:
                pass
            await asyncio.sleep(0.5)

    duration = (datetime.now() - start_time).total_seconds()

    report = (
        "✅ **Xabar tarqatish yakunlandi!**\n\n"
        f"📤 **Muvaffaqiyatli yetkazildi:** {sent_count} ta\n"
        f"🚫 **Botni bloklaganlar:** {blocked_count} ta\n"
        f"❌ **Xatoliklar:** {failed_count} ta\n"
        f"⏱ **Ketgan vaqt:** {duration:.1f} soniya"
    )

    kb = await get_admin_main_keyboard()
    try:
        await status_msg.edit_text(report, reply_markup=kb, parse_mode="Markdown")
    except Exception:
        await callback.message.answer(report, reply_markup=kb, parse_mode="Markdown")
    await callback.answer("Tarqatish yakunlandi!")


@admin_router.callback_query(F.data == "noop")
async def cb_noop(callback: CallbackQuery) -> None:
    await callback.answer()


@admin_router.callback_query(F.data.startswith("admin:"))
async def cb_admin_unauthorized(callback: CallbackQuery) -> None:
    """Admin bo'lmagan foydalanuvchi admin tugmalarini bosganda ogohlantirish"""
    await callback.answer("⛔ Siz bot admini emassiz!", show_alert=True)

