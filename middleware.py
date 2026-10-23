import logging
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery

import database
from admin import notify_admins_about_new_user

logger = logging.getLogger(__name__)


class UserTrackerMiddleware(BaseMiddleware):
    """Barcha kiruvchi xabarlar va tugma bosilishlarida foydalanuvchini bazaga yozib boruvchi middleware"""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        bot = data.get("bot")
        user = getattr(event, "from_user", None)

        if user and not user.is_bot:
            action = "faollik"
            if isinstance(event, Message):
                if event.text:
                    if event.text.startswith("/"):
                        action = f"Komanda: {event.text.split()[0]}"
                    elif event.text in [
                        "🤖 AI Chat Bo'limi",
                        "📥 Video Yuklash",
                        "🔘 Dumaloq Video",
                        "⚙️ Admin Panel",
                        "🔄 Yangi suhbat boshlash",
                        "🔙 Asosiy menyuga qaytish"
                    ]:
                        action = event.text
                    else:
                        action = "Xabar / Havola"
                elif event.video:
                    action = "Video yubordi"
                elif event.document:
                    action = "Hujjat yubordi"
                elif event.photo:
                    action = "Rasm yubordi"
                elif event.voice or event.video_note:
                    action = "Ovoz / Dumaloq video"
                else:
                    action = "Boshqa media"
            elif isinstance(event, CallbackQuery):
                c_data = event.data or ""
                action = f"Tugma: {c_data[:25]}"

            try:
                is_new, user_data = await database.add_or_update_user(
                    user_id=user.id,
                    username=user.username,
                    first_name=user.first_name,
                    last_name=user.last_name,
                    action=action
                )

                # Agar foydalanuvchi bot admini tomonidan bloklangan bo'lsa
                if user_data.get("is_banned") == 1:
                    if isinstance(event, Message):
                        await event.answer("⛔ **Siz ushbu botdan foydalanish huquqidan mahrum qilingansiz.**")
                    elif isinstance(event, CallbackQuery):
                        await event.answer("⛔ Siz botda bloklangansiz!", show_alert=True)
                    return None

                # Agar yangi a'zo bo'lsa, adminga xabar yuborish
                if is_new and bot:
                    try:
                        await notify_admins_about_new_user(bot, user_data)
                    except Exception as e:
                        logger.warning(f"Adminga yangi a'zo xabarnomasini yuborishda xatolik: {e}")

            except Exception as e:
                logger.error(f"Foydalanuvchi statistikasini saqlashda xatolik: {e}", exc_info=True)

        return await handler(event, data)
