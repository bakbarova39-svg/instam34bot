import sqlite3
import os
import csv
import asyncio
from datetime import datetime
from contextlib import contextmanager
from typing import List, Dict, Any, Optional, Tuple, Generator

DB_PATH = os.path.join(os.path.dirname(__file__), "bot_database.db")


@contextmanager
def get_db() -> Generator[sqlite3.Connection, None, None]:
    """Ma'lumotlar bazasi ulanishini ochish, kommit qilish va xavfsiz yopish uchun contextmanager"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """Ma'lumotlar bazasi jadvallarini yaratish va boshlang'ich sozlamalarni o'rnatish"""
    with get_db() as conn:
        cursor = conn.cursor()
        # Foydalanuvchilar jadvali
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                joined_at TEXT,
                last_active TEXT,
                usage_count INTEGER DEFAULT 1,
                last_action TEXT DEFAULT 'start',
                is_banned INTEGER DEFAULT 0
            )
        """)

        # Admin sozlamalari jadvali
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)

        # Boshlang'ich sozlamalar (Yangi foydalanuvchi haqida xabarnoma berish)
        cursor.execute("""
            INSERT OR IGNORE INTO settings (key, value)
            VALUES ('notify_new_users', '1')
        """)


# --- FOYDALANUVCHILARNI QO'SHISH VA YANGILASH ---

def _add_or_update_user_sync(
    user_id: int,
    username: Optional[str],
    first_name: Optional[str],
    last_name: Optional[str],
    action: str = "faollik"
) -> Tuple[bool, Dict[str, Any]]:
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    clean_username = username.lstrip("@") if username else None
    clean_first_name = first_name or ""
    clean_last_name = last_name or ""

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()

        if row is None:
            # Yangi foydalanuvchi
            cursor.execute("""
                INSERT INTO users (
                    user_id, username, first_name, last_name,
                    joined_at, last_active, usage_count, last_action, is_banned
                ) VALUES (?, ?, ?, ?, ?, ?, 1, ?, 0)
            """, (user_id, clean_username, clean_first_name, clean_last_name, now_str, now_str, action))
            return True, {
                "user_id": user_id,
                "username": clean_username,
                "first_name": clean_first_name,
                "last_name": clean_last_name,
                "joined_at": now_str,
                "last_active": now_str,
                "usage_count": 1,
                "last_action": action,
                "is_banned": 0
            }
        else:
            # Mavjud foydalanuvchi ma'lumotlarini yangilash
            cursor.execute("""
                UPDATE users SET
                    username = ?,
                    first_name = ?,
                    last_name = ?,
                    last_active = ?,
                    usage_count = usage_count + 1,
                    last_action = ?
                WHERE user_id = ?
            """, (clean_username, clean_first_name, clean_last_name, now_str, action, user_id))
            user_data = dict(row)
            user_data["username"] = clean_username
            user_data["first_name"] = clean_first_name
            user_data["last_name"] = clean_last_name
            user_data["last_active"] = now_str
            user_data["usage_count"] += 1
            user_data["last_action"] = action
            return False, user_data


async def add_or_update_user(
    user_id: int,
    username: Optional[str],
    first_name: Optional[str],
    last_name: Optional[str],
    action: str = "faollik"
) -> Tuple[bool, Dict[str, Any]]:
    return await asyncio.to_thread(
        _add_or_update_user_sync, user_id, username, first_name, last_name, action
    )


# --- STATISTIKA ---

def _get_stats_sync() -> Dict[str, Any]:
    with get_db() as conn:
        cursor = conn.cursor()

        # Jami foydalanuvchilar
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]

        # Bugun faol bo'lganlar
        cursor.execute("""
            SELECT COUNT(*) FROM users 
            WHERE date(last_active) = date('now', 'localtime')
        """)
        active_today = cursor.fetchone()[0]

        # Bugun yangi qo'shilganlar
        cursor.execute("""
            SELECT COUNT(*) FROM users 
            WHERE date(joined_at) = date('now', 'localtime')
        """)
        new_today = cursor.fetchone()[0]

        # Oxirgi 7 kunda faol bo'lganlar
        cursor.execute("""
            SELECT COUNT(*) FROM users 
            WHERE last_active >= datetime('now', '-7 days', 'localtime')
        """)
        active_week = cursor.fetchone()[0]

        # Oxirgi 30 kunda faol bo'lganlar
        cursor.execute("""
            SELECT COUNT(*) FROM users 
            WHERE last_active >= datetime('now', '-30 days', 'localtime')
        """)
        active_month = cursor.fetchone()[0]

        # Jami amallar / so'rovlar soni
        cursor.execute("SELECT COALESCE(SUM(usage_count), 0) FROM users")
        total_actions = cursor.fetchone()[0]

        # Bloklanganlar
        cursor.execute("SELECT COUNT(*) FROM users WHERE is_banned = 1")
        banned_users = cursor.fetchone()[0]

        return {
            "total_users": total_users,
            "active_today": active_today,
            "new_today": new_today,
            "active_week": active_week,
            "active_month": active_month,
            "total_actions": total_actions,
            "banned_users": banned_users
        }


async def get_stats() -> Dict[str, Any]:
    return await asyncio.to_thread(_get_stats_sync)


# --- FOYDALANUVCHILAR RO'YXATI VA QIDIRUV ---

def _get_users_page_sync(limit: int = 10, offset: int = 0) -> Tuple[List[Dict[str, Any]], int]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        total = cursor.fetchone()[0]

        cursor.execute("""
            SELECT * FROM users
            ORDER BY last_active DESC
            LIMIT ? OFFSET ?
        """, (limit, offset))
        rows = [dict(row) for row in cursor.fetchall()]
        return rows, total


async def get_users_page(limit: int = 10, offset: int = 0) -> Tuple[List[Dict[str, Any]], int]:
    return await asyncio.to_thread(_get_users_page_sync, limit, offset)


def _get_user_sync(user_id: int) -> Optional[Dict[str, Any]]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


async def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    return await asyncio.to_thread(_get_user_sync, user_id)


def _search_users_sync(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    query = query.strip()
    with get_db() as conn:
        cursor = conn.cursor()
        if query.isdigit():
            # ID bo'yicha qidirish
            cursor.execute("""
                SELECT * FROM users
                WHERE user_id = ? OR CAST(user_id AS TEXT) LIKE ?
                ORDER BY last_active DESC
                LIMIT ?
            """, (int(query), f"%{query}%", limit))
        else:
            clean_q = query.lstrip("@")
            cursor.execute("""
                SELECT * FROM users
                WHERE username LIKE ? OR first_name LIKE ? OR last_name LIKE ?
                ORDER BY last_active DESC
                LIMIT ?
            """, (f"%{clean_q}%", f"%{query}%", f"%{query}%", limit))
        return [dict(row) for row in cursor.fetchall()]


async def search_users(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    return await asyncio.to_thread(_search_users_sync, query, limit)


def _set_ban_status_sync(user_id: int, is_banned: int) -> bool:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET is_banned = ? WHERE user_id = ?", (is_banned, user_id))
        return cursor.rowcount > 0


async def set_ban_status(user_id: int, is_banned: int) -> bool:
    return await asyncio.to_thread(_set_ban_status_sync, user_id, is_banned)


def _get_all_broadcast_user_ids_sync() -> List[int]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users WHERE is_banned = 0")
        return [row[0] for row in cursor.fetchall()]


async def get_all_broadcast_user_ids() -> List[int]:
    return await asyncio.to_thread(_get_all_broadcast_user_ids_sync)


# --- EXCEL / CSV EKSPORT ---

def _export_users_csv_sync(filepath: str) -> int:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users ORDER BY joined_at ASC")
        rows = cursor.fetchall()

        with open(filepath, mode="w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Telegram ID",
                "Username",
                "Ism",
                "Familiya",
                "Botga qo'shilgan sana",
                "Oxirgi faollik",
                "Foydalanishlar soni",
                "Oxirgi bajargan amali",
                "Bloklangan holati"
            ])
            for r in rows:
                writer.writerow([
                    r["user_id"],
                    f"@{r['username']}" if r["username"] else "Mavjud emas",
                    r["first_name"] or "",
                    r["last_name"] or "",
                    r["joined_at"],
                    r["last_active"],
                    r["usage_count"],
                    r["last_action"] or "",
                    "Ha (Bloklangan)" if r["is_banned"] else "Yo'q (Faol)"
                ])
        return len(rows)


async def export_users_csv(filepath: str) -> int:
    return await asyncio.to_thread(_export_users_csv_sync, filepath)


# --- ADMIN SOZLAMALARI ---

def _get_setting_sync(key: str, default: str = "") -> str:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row[0] if row else default


async def get_setting(key: str, default: str = "") -> str:
    return await asyncio.to_thread(_get_setting_sync, key, default)


def _set_setting_sync(key: str, value: str) -> None:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO settings (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """, (key, value))


async def set_setting(key: str, value: str) -> None:
    await asyncio.to_thread(_set_setting_sync, key, value)


def _toggle_setting_sync(key: str) -> str:
    curr = _get_setting_sync(key, "0")
    new_val = "0" if curr == "1" else "1"
    _set_setting_sync(key, new_val)
    return new_val


async def toggle_setting(key: str) -> str:
    return await asyncio.to_thread(_toggle_setting_sync, key)
