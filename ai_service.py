import os
import logging
from typing import Dict, List
import aiohttp
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Foydalanuvchilarning suhbat konteksti (xotirasi)
user_conversations: Dict[int, List[Dict[str, str]]] = {}

SYSTEM_PROMPT = (
    "Siz Telegram bot ichidagi aqlli, do'stona va har tomonlama bilimdon sun'iy intellekt (AI) yordamchisiz. "
    "Foydalanuvchilarning barcha turdagi savollariga (ilm-fan, axborot texnologiyalari, dasturlash, maslahatlar, "
    "tarjimalar, ta'lim, ijodiy yozishmalar va h.k.) aniq, to'g'ri, samimiy va chiroyli o'zbek tilida javob bering. "
    "Javoblaringiz tushunarli, asosli va lo'nda bo'lsin."
)


async def _ask_gemini_model(model_name: str, payload: dict, session: aiohttp.ClientSession) -> str:
    """Muayyan Gemini modeli orqali so'rov yuborish"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
    async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=20)) as resp:
        if resp.status == 200:
            data = await resp.json()
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    return parts[0].get("text", "").strip()
        error_text = await resp.text()
        logger.warning(f"Gemini ({model_name}) API xatosi (status {resp.status}): {error_text[:200]}")
        raise Exception(f"Gemini API ({model_name}) javob bermadi (status {resp.status})")


async def _ask_gemini(user_id: int, user_message: str, history: List[Dict[str, str]]) -> str:
    """Rasmiy Google Gemini API orqali javob olish (ishonchli modellar ketma-ketligi bilan)"""
    contents = []
    for msg in history[-6:]:
        role = "user" if msg["role"] == "user" else "model"
        contents.append({"role": role, "parts": [{"text": msg["content"]}]})

    contents.append({"role": "user", "parts": [{"text": user_message}]})

    payload = {
        "system_instruction": {
            "parts": [{"text": SYSTEM_PROMPT}]
        },
        "contents": contents
    }

    # Ketma-ket tekshiriladigan barqaror modellar ro'yxati
    models_to_try = ["gemini-3.5-flash", "gemini-3.5-flash-lite", "gemini-3.8-flash"]

    async with aiohttp.ClientSession() as session:
        last_err = None
        for model in models_to_try:
            try:
                return await _ask_gemini_model(model, payload, session)
            except Exception as e:
                last_err = e
                continue
        if last_err:
            raise last_err
        raise Exception("Hech bir Gemini modeli javob bermadi.")


async def _ask_g4f(user_id: int, user_message: str, history: List[Dict[str, str]]) -> str:
    """Zaxira (fallback) sifatida g4f orqali javob olish"""
    from g4f.client import AsyncClient

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(history[-6:])
    messages.append({"role": "user", "content": user_message})

    client = AsyncClient()
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages
    )
    ai_reply = response.choices[0].message.content
    if not ai_reply:
        raise ValueError("AI dan bo'sh javob keldi.")
    return ai_reply.strip()


async def ask_ai(user_id: int, user_message: str) -> str:
    """Foydalanuvchi savoliga sun'iy intellekt orqali javob berish (kontekstni saqlagan holda)."""
    if user_id not in user_conversations:
        user_conversations[user_id] = []

    history = user_conversations[user_id]
    ai_reply = None

    # 1-navbatda agar GEMINI_API_KEY mavjud bo'lsa, rasmiy Google Gemini'dan foydalanish
    if GEMINI_API_KEY and GEMINI_API_KEY.strip():
        try:
            ai_reply = await _ask_gemini(user_id, user_message, history)
        except Exception as e:
            logger.error(f"Gemini chaqiruvida xatolik, zaxira tizimiga o'tilmoqda: {e}")

    # 2-navbatda (zaxira tizimi)
    if not ai_reply:
        try:
            ai_reply = await _ask_g4f(user_id, user_message, history)
        except Exception as e:
            logger.error(f"Zaxira AI xizmatida xatolik: {e}", exc_info=True)

    if not ai_reply:
        return (
            "⚠️ Kechirasiz, sun'iy intellekt xizmati bilan bog'lanishda vaqtinchalik xatolik yuz berdi.\n"
            "Iltimos, bir ozdan so'ng savolingizni qaytadan yuboring."
        )

    # Suhbat tarixini yangilash
    history.append({"role": "user", "content": user_message})
    history.append({"role": "assistant", "content": ai_reply})

    if len(history) > 10:
        user_conversations[user_id] = history[-10:]

    return ai_reply


def reset_chat(user_id: int) -> None:
    """Foydalanuvchi suhbat tarixini o'chirish (tozalash)."""
    if user_id in user_conversations:
        user_conversations[user_id] = []
