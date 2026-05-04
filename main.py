import asyncio
import logging
from collections import Counter
from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    LabeledPrice, PreCheckoutQuery, KeyboardButton, ReplyKeyboardMarkup,
    ReplyKeyboardRemove, Contact
)
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.exceptions import TelegramForbiddenError
from datetime import datetime, timedelta
import json
import aiohttp
import secrets
import aiosqlite
import os


# ==================== КОНФИГ ====================
BOT_TOKEN = os.getenv("BOT_TOKEN")
BOT_USERNAME = "GiftsBearBot"
OWNER_ID = 7654716032
OWNER_COMMISSION = 10
BANNER_FILE_ID = "https://i.ibb.co/mVcFVNc8/Gemini-Generated-Image-gs58kzgs58kzgs58-1.png"
DB_PATH = "bot_data.db"

GIFTS = {
    "bear_easter": {
        "id": "5969796561943660080",
        "name": "Мишка на Пасху",
        "emoji": "🐣",
        "price_stars": 60,
        "real_price": 50,
        "description": "Пасхальный мишка 🐣",
        "sticker_id": "CAACAgIAAxkBAAEdDRtp2uGUE4sq8p41rbPyG_Ch7ZFU3gACaJYAAuUn2EoGyAF1OUuSqzsE"
    },
    "bear_ny": {
        "id": "5956217000635139069",
        "name": "Новогодний мишка",
        "emoji": "🧸",
        "price_stars": 60,
        "real_price": 50,
        "description": "Новогодний плюшевый мишка 🎄",
        "sticker_id": "CAACAgIAAxkBAAEc8JBp1r0wJIedvEkkqQ7wE_-CFb-i7wACaIUAAi9FqUoeMNsMreDLHjsE"
    },
    "bear_val": {
        "id": "5800655655995968830",
        "name": "Мишка на 14 февраля",
        "emoji": "🧸",
        "price_stars": 60,
        "real_price": 50,
        "description": "Валентинка для любимого человека 💝",
        "sticker_id": "CAACAgIAAxkBAAEc8Ipp1ry79Gv3McjdIaBajuFhDvdyIQACqY0AAnMkiEh9grk01NKMIjsE"
    },
    "bear_feb8": {
        "id": "5866352046986232958",
        "name": "Мишка на 8 февраля",
        "emoji": "🧸",
        "price_stars": 60,
        "real_price": 50,
        "description": "Мишка на 8 февраля 💐",
        "sticker_id": None
    },
    "bear_patrick": {
        "id": "5893356958802511476",
        "name": "Мишка на день Патрика",
        "emoji": "🍀",
        "price_stars": 60,
        "real_price": 50,
        "description": "Мишка ко Дню святого Патрика 🍀",
        "sticker_id": "CAACAgIAAxkBAAEc9R1p14e-r8TfMYhez682L2z0wtrV4QACh5MAAtUqyEkxeMWoJpbPnTsE"
    },
    "bear_april": {
        "id": "5935895822435615975",
        "name": "Первый апрельский мишка",
        "emoji": "🤡",
        "price_stars": 60,
        "real_price": 50,
        "description": "Первоапрельский сюрприз 🎉",
        "sticker_id": "CAACAgIAAxkBAAEc9Rtp14eiK9M51qRo4uCUH4XsXZbPjwACCZIAAlm7aErtjg8w1WCJ0DsE"
    }
}

SEASONAL_GIFTS = {
    "tree": {
        "id": "5922558454332916696",
        "name": "Ёлка на Новый год",
        "emoji": "🎄",
        "price_stars": 60,
        "real_price": 50,
        "description": "Праздничная ёлочка — 31 декабря 🥂",
        "sticker_id": "CAACAgIAAxkBAAEc8JJp1r1LYrNBavhZL0_YE2oiknj5xwAC3ZEAAnlyMEp8bdv6MLbzCjsE"
    },
    "heart": {
        "id": "5801108895304779062",
        "name": "Сердце любви",
        "emoji": "❤️",
        "price_stars": 60,
        "real_price": 50,
        "description": "Подарок с любовью — 14 февраля 💕",
        "sticker_id": "CAACAgIAAxkBAAEc8JRp1r1avUwU-jXB4P5c6ZMdxEdcgQAC4osAAqyWiUiHPzhHi5F_rzsE"
    },
}

ALL_GIFTS = {**GIFTS, **SEASONAL_GIFTS}

SIMPLE_GIFTS = {
    "simple_heart": {
        "id": "5170145012310081615",
        "name": "Простое сердце",
        "emoji": "❤️",
        "price_stars": 0,
        "real_price": 0,
        "description": "Обычное сердце",
        "sticker_id": None
    },
}

# ==================== БАЗА ДАННЫХ ====================

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                joined_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                gift_key TEXT NOT NULL,
                gift_name TEXT NOT NULL,
                emoji TEXT NOT NULL,
                target TEXT NOT NULL,
                friend_id INTEGER,
                stars INTEGER NOT NULL,
                date TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS pending_gifts (
                token TEXT PRIMARY KEY,
                buyer_id INTEGER NOT NULL,
                gift_key TEXT NOT NULL,
                message_text TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS pending_payments (
                token TEXT PRIMARY KEY,
                gift_key TEXT NOT NULL,
                target TEXT NOT NULL,
                extra TEXT NOT NULL,
                anonymous INTEGER NOT NULL,
                message_text TEXT NOT NULL,
                buyer_id INTEGER NOT NULL,
                used_promo TEXT,
                invoice_msg_id INTEGER,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS gift_sales (
                gift_key TEXT PRIMARY KEY,
                sale_price INTEGER NOT NULL,
                original_price INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS promo_codes (
                code TEXT PRIMARY KEY,
                discount_stars INTEGER NOT NULL,
                activations_left INTEGER NOT NULL,
                total_activations INTEGER NOT NULL,
                gift_key TEXT,
                expires_at TEXT NOT NULL,
                used_by TEXT NOT NULL DEFAULT '[]'
            );

            CREATE TABLE IF NOT EXISTS active_user_promos (
                user_id INTEGER PRIMARY KEY,
                code TEXT NOT NULL,
                discount INTEGER NOT NULL,
                gift_key TEXT
            );

            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS custom_gifts (
                gift_key TEXT PRIMARY KEY,
                gift_id TEXT NOT NULL,
                name TEXT NOT NULL,
                emoji TEXT NOT NULL,
                price_stars INTEGER NOT NULL,
                description TEXT NOT NULL,
                sticker_id TEXT,
                created_at TEXT NOT NULL
            );
        """)
        # Миграция: добавляем invoice_msg_id если колонки нет
        try:
            await db.execute("ALTER TABLE pending_payments ADD COLUMN invoice_msg_id INTEGER")
            await db.commit()
        except Exception:
            pass  # Колонка уже существует
        await db.commit()

# --- Users ---

async def db_add_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, joined_at) VALUES (?, ?)",
            (user_id, datetime.now().strftime("%d.%m.%Y %H:%M"))
        )
        await db.commit()

async def db_get_all_users() -> list[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id FROM users") as cursor:
            rows = await cursor.fetchall()
    return [r[0] for r in rows]

async def db_count_users() -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as cursor:
            row = await cursor.fetchone()
    return row[0]

async def db_remove_user(user_id: int):
    """Удаляет пользователя из базы (заблокировал бота)."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        await db.commit()

# --- History ---

async def db_add_history(user_id: int, record: dict):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO history
               (user_id, gift_key, gift_name, emoji, target, friend_id, stars, date)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                user_id,
                record["gift_key"],
                record["gift_name"],
                record["emoji"],
                record["target"],
                record.get("friend_id"),
                record["stars"],
                record["date"],
            )
        )
        await db.commit()

async def db_get_history(user_id: int) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM history WHERE user_id = ? ORDER BY id DESC LIMIT 10",
            (user_id,)
        ) as cursor:
            rows = await cursor.fetchall()
    return [dict(r) for r in reversed(rows)]

async def db_all_history() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM history") as cursor:
            rows = await cursor.fetchall()
    return [dict(r) for r in rows]

# --- Pending gifts (ссылочные подарки) ---

async def db_set_pending_gift(token: str, data: dict):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT OR REPLACE INTO pending_gifts
               (token, buyer_id, gift_key, message_text, created_at) VALUES (?, ?, ?, ?, ?)""",
            (token, data["buyer_id"], data["gift_key"], data.get("message_text", ""),
             datetime.now().strftime("%d.%m.%Y %H:%M"))
        )
        await db.commit()

async def db_pop_pending_gift(token: str) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM pending_gifts WHERE token = ?", (token,)) as cursor:
            row = await cursor.fetchone()
        if not row:
            return None
        await db.execute("DELETE FROM pending_gifts WHERE token = ?", (token,))
        await db.commit()
    return dict(row)

async def db_count_pending_gifts() -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM pending_gifts") as cursor:
            row = await cursor.fetchone()
    return row[0]

async def db_update_pending_gift_text(token: str, text: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE pending_gifts SET message_text = ? WHERE token = ?", (text, token)
        )
        await db.commit()

# --- Pending payments ---

async def db_set_pending_payment(token: str, data: dict):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT OR REPLACE INTO pending_payments
               (token, gift_key, target, extra, anonymous, message_text, buyer_id, used_promo, invoice_msg_id, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                token,
                data["gift_key"],
                data["target"],
                data.get("extra", ""),
                1 if data.get("anonymous") else 0,
                data.get("message_text", ""),
                data["buyer_id"],
                data.get("used_promo"),
                data.get("invoice_msg_id"),
                datetime.now().strftime("%d.%m.%Y %H:%M"),
            )
        )
        await db.commit()

async def db_pop_pending_payment(token: str) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM pending_payments WHERE token = ?", (token,)) as cursor:
            row = await cursor.fetchone()
        if not row:
            return None
        await db.execute("DELETE FROM pending_payments WHERE token = ?", (token,))
        await db.commit()
    d = dict(row)
    d["anonymous"] = bool(d["anonymous"])
    return d

# --- Gift sales (скидки) ---

async def db_set_sale(gift_key: str, sale_price: int, original_price: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO gift_sales (gift_key, sale_price, original_price) VALUES (?, ?, ?)",
            (gift_key, sale_price, original_price)
        )
        await db.commit()

async def db_remove_sale(gift_key: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM gift_sales WHERE gift_key = ?", (gift_key,))
        await db.commit()

async def db_get_all_sales() -> dict[str, dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM gift_sales") as cursor:
            rows = await cursor.fetchall()
    return {r["gift_key"]: {"sale_price": r["sale_price"], "original_price": r["original_price"]} for r in rows}

async def db_get_sale(gift_key: str) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM gift_sales WHERE gift_key = ?", (gift_key,)) as cursor:
            row = await cursor.fetchone()
    return dict(row) if row else None

# --- Promo codes ---

async def db_set_promo(code: str, data: dict):
    async with aiosqlite.connect(DB_PATH) as db:
        used_by = json.dumps(list(data.get("used_by", [])))
        expires_at = data["expires_at"].strftime("%Y-%m-%d %H:%M:%S") if isinstance(data["expires_at"], datetime) else data["expires_at"]
        await db.execute(
            """INSERT OR REPLACE INTO promo_codes
               (code, discount_stars, activations_left, total_activations, gift_key, expires_at, used_by)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (code, data["discount_stars"], data["activations_left"],
             data["total_activations"], data.get("gift_key"), expires_at, used_by)
        )
        await db.commit()

async def db_get_promo(code: str) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM promo_codes WHERE code = ?", (code,)) as cursor:
            row = await cursor.fetchone()
    if not row:
        return None
    d = dict(row)
    d["used_by"] = set(json.loads(d["used_by"]))
    d["expires_at"] = datetime.strptime(d["expires_at"], "%Y-%m-%d %H:%M:%S")
    return d

async def db_get_all_promos() -> dict[str, dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM promo_codes") as cursor:
            rows = await cursor.fetchall()
    result = {}
    for row in rows:
        d = dict(row)
        d["used_by"] = set(json.loads(d["used_by"]))
        d["expires_at"] = datetime.strptime(d["expires_at"], "%Y-%m-%d %H:%M:%S")
        result[d["code"]] = d
    return result

async def db_delete_promo(code: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM promo_codes WHERE code = ?", (code,))
        await db.commit()

async def db_promo_use(code: str, user_id: int):
    """Уменьшает счётчик активаций и добавляет юзера в used_by."""
    promo = await db_get_promo(code)
    if not promo:
        return
    promo["activations_left"] -= 1
    promo["used_by"].add(user_id)
    if promo["activations_left"] <= 0:
        await db_delete_promo(code)
    else:
        await db_set_promo(code, promo)

# --- Active user promos ---

async def db_set_user_promo(user_id: int, code: str, discount: int, gift_key: str | None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO active_user_promos (user_id, code, discount, gift_key) VALUES (?, ?, ?, ?)",
            (user_id, code, discount, gift_key)
        )
        await db.commit()

async def db_get_user_promo(user_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM active_user_promos WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
    return dict(row) if row else None

async def db_delete_user_promo(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM active_user_promos WHERE user_id = ?", (user_id,))
        await db.commit()

async def db_get_users_with_promo(code: str) -> list[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT user_id FROM active_user_promos WHERE code = ?", (code,)
        ) as cursor:
            rows = await cursor.fetchall()
    return [r[0] for r in rows]

async def db_delete_promo_from_users(code: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM active_user_promos WHERE code = ?", (code,))
        await db.commit()

# --- Settings (maintenance_mode и др.) ---

async def db_get_setting(key: str, default: str = "") -> str:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT value FROM settings WHERE key = ?", (key,)) as cursor:
            row = await cursor.fetchone()
    return row[0] if row else default

async def db_set_setting(key: str, value: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value)
        )
        await db.commit()

# --- Custom gifts (добавленные через админку) ---

async def db_add_custom_gift(gift_key: str, data: dict):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT OR REPLACE INTO custom_gifts
               (gift_key, gift_id, name, emoji, price_stars, description, sticker_id, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                gift_key,
                data["id"],
                data["name"],
                data["emoji"],
                data["price_stars"],
                data["description"],
                data.get("sticker_id"),
                datetime.now().strftime("%d.%m.%Y %H:%M"),
            )
        )
        await db.commit()

async def db_delete_custom_gift(gift_key: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM custom_gifts WHERE gift_key = ?", (gift_key,))
        await db.commit()

async def db_get_all_custom_gifts() -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM custom_gifts") as cursor:
            rows = await cursor.fetchall()
    result = {}
    for row in rows:
        d = dict(row)
        key = d["gift_key"]
        result[key] = {
            "id": d["gift_id"],
            "name": d["name"],
            "emoji": d["emoji"],
            "price_stars": d["price_stars"],
            "real_price": d["price_stars"],
            "description": d["description"],
            "sticker_id": d.get("sticker_id"),
        }
    return result

async def load_custom_gifts_to_memory():
    """Загружает кастомные подарки из БД в ALL_GIFTS и GIFTS."""
    custom = await db_get_all_custom_gifts()
    for key, gift in custom.items():
        GIFTS[key] = gift
        ALL_GIFTS[key] = gift

# ==================== РЕЖИМ ОБСЛУЖИВАНИЯ (в памяти, синхронизируется с БД) ====================
maintenance_mode: bool = False

# ==================== FSM ====================
class GiftStates(StatesGroup):
    selecting_gift_reply = State()
    selecting_seasonal_gift_reply = State()
    selecting_whom_reply = State()
    choosing_gift_for_friend = State()
    waiting_contact = State()
    entering_friend_id = State()
    choosing_gift_for_self = State()
    ask_comment = State()
    entering_comment = State()
    entering_promo = State()
    admin_broadcast = State()
    admin_select_gift = State()
    admin_edit_field = State()
    admin_enter_value = State()
    admin_enter_sale_price = State()
    admin_promo_name = State()
    admin_promo_discount = State()
    admin_promo_gift = State()
    admin_promo_activations = State()
    admin_promo_hours = State()
    admin_promo_target = State()
    admin_promo_userid = State()
    owner_send_userid = State()
    owner_send_gift = State()
    owner_send_comment = State()
    owner_simple_userid = State()
    owner_simple_gift = State()
    owner_simple_comment = State()
    ask_anon = State()
    # Добавление нового подарка
    admin_add_gift_id = State()
    admin_add_gift_name = State()
    admin_add_gift_emoji = State()
    admin_add_gift_price = State()
    admin_add_gift_desc = State()
    admin_add_gift_confirm = State()
    # Удаление кастомного подарка
    admin_del_gift_select = State()

# ==================== УТИЛИТЫ ЦЕНЫ ====================

async def get_gift_price(gift_key: str) -> int:
    sale = await db_get_sale(gift_key)
    if sale:
        return sale["sale_price"]
    return ALL_GIFTS[gift_key]["price_stars"]

async def get_gift_price_for_user(gift_key: str, user_id: int) -> int:
    base = await get_gift_price(gift_key)
    promo = await db_get_user_promo(user_id)
    if promo:
        promo_gift = promo.get("gift_key")
        if promo_gift is None or promo_gift == gift_key:
            return max(1, base - promo["discount"])
    return base

async def get_price_display_for_user(gift_key: str, user_id: int) -> str:
    base_price = await get_gift_price(gift_key)
    promo = await db_get_user_promo(user_id)
    if promo:
        promo_gift = promo.get("gift_key")
        if promo_gift is None or promo_gift == gift_key:
            discounted = max(1, base_price - promo["discount"])
            return f"{discounted} ⭐  <s>{base_price} ⭐</s> 🎟️ -{promo['discount']} ⭐"
    return await get_price_display(gift_key)

async def get_price_display(gift_key: str) -> str:
    gift = ALL_GIFTS[gift_key]
    sale = await db_get_sale(gift_key)
    if sale:
        return f"{sale['sale_price']} ⭐  <s>{sale['original_price']} ⭐</s>"
    return f"{gift['price_stars']} ⭐"

# ==================== КЛАВИАТУРЫ ====================

def main_reply_kb(user_id: int = 0) -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton(text="🎁 Купить подарок"), KeyboardButton(text="📜 История")],
        [KeyboardButton(text="🎄 Отдельные подарки"), KeyboardButton(text="🎟️ Промокод")],
    ]
    if user_id == OWNER_ID:
        rows.append([KeyboardButton(text="⚙️ Админ панель")])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True, persistent=True)

async def gifts_list_reply_kb(target: str) -> ReplyKeyboardMarkup:
    rows = []
    for key, gift in GIFTS.items():
        price = await get_gift_price(key)
        sale = await db_get_sale(key)
        if sale:
            label = f"{gift['name']} — {price} ⭐ (было {sale['original_price']})"
        else:
            label = f"{gift['name']} — {price} ⭐"
        rows.append([KeyboardButton(text=label)])
    rows.append([KeyboardButton(text="◀️ Назад")])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True, one_time_keyboard=True)

async def seasonal_gifts_list_reply_kb(target: str) -> ReplyKeyboardMarkup:
    rows = []
    for key, gift in SEASONAL_GIFTS.items():
        price = await get_gift_price(key)
        sale = await db_get_sale(key)
        if sale:
            label = f"{gift['name']} — {price} ⭐ (було {sale['original_price']})"
        else:
            label = f"{gift['name']} — {price} ⭐"
        rows.append([KeyboardButton(text=label)])
    rows.append([KeyboardButton(text="◀️ Назад")])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True, one_time_keyboard=True)

async def gift_keys_by_text() -> dict:
    result = {}
    for key, gift in ALL_GIFTS.items():
        price = await get_gift_price(key)
        sale = await db_get_sale(key)
        if sale:
            result[f"{gift['name']} — {price} ⭐ (было {sale['original_price']})"] = key
            result[f"{gift['name']} — {price} ⭐ (було {sale['original_price']})"] = key
        else:
            result[f"{gift['name']} — {price} ⭐"] = key
    return result

def whom_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👤 Себе"), KeyboardButton(text="👥 Другу")],
            [KeyboardButton(text="◀️ Назад")],
        ],
        resize_keyboard=True, one_time_keyboard=True
    )

def anon_choice_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎭 Анонимно"), KeyboardButton(text="👤 От своего имени")],
            [KeyboardButton(text="◀️ Назад")],
        ],
        resize_keyboard=True, one_time_keyboard=True
    )

def yes_no_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ Да"), KeyboardButton(text="❌ Нет")],
            [KeyboardButton(text="◀️ Назад")],
        ],
        resize_keyboard=True, one_time_keyboard=True
    )

def cancel_only_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]],
        resize_keyboard=True, one_time_keyboard=True
    )

async def main_menu_kb(user_id: int = 0) -> InlineKeyboardMarkup:
    promo = await db_get_user_promo(user_id)
    promo_label = f"🎟️ Промокод активен: -{promo['discount']} ⭐" if promo else "🎟️ Ввести промокод"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 Купить подарок", callback_data="buy_gift")],
        [InlineKeyboardButton(text="📜 История подарков", callback_data="gift_history")],
        [InlineKeyboardButton(text=promo_label, callback_data="enter_promo")],
    ])

def buy_for_whom_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎀 Купить себе", callback_data="buy_for_self")],
        [InlineKeyboardButton(text="💝 Купить другу", callback_data="buy_for_friend")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")],
    ])

async def confirm_buy_kb(gift_key: str, target: str, extra: str = "", user_id: int = 0) -> InlineKeyboardMarkup:
    price = await get_gift_price_for_user(gift_key, user_id)
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"💳 Оплатить {price} ⭐",
            callback_data=f"pay:{gift_key}:{target}:{extra}"
        )],
    ])

# ==================== АДМИН КЛАВИАТУРЫ ====================

def admin_main_kb() -> ReplyKeyboardMarkup:
    maintenance_label = "🟢 Вкл. обслуживание" if not maintenance_mode else "🔴 Выкл. обслуживание"
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📢 Рассылка"), KeyboardButton(text="🎁 Редактировать подарки")],
            [KeyboardButton(text="📊 Статистика"), KeyboardButton(text="🎟️ Промокоды")],
            [KeyboardButton(text="🎀 Отправить подарок"), KeyboardButton(text=maintenance_label)],
            [KeyboardButton(text="💝 Простые подарки"), KeyboardButton(text="➕ Добавить подарок")],
            [KeyboardButton(text="🗑️ Удалить подарок"), KeyboardButton(text="◀️ Главное меню")],
        ],
        resize_keyboard=True, persistent=True
    )

async def admin_gifts_kb() -> ReplyKeyboardMarkup:
    rows = []
    for key, gift in ALL_GIFTS.items():
        sale = await db_get_sale(key)
        sale_mark = " 🔥" if sale else ""
        rows.append([KeyboardButton(text=f"{gift['emoji']} {gift['name']}{sale_mark}")])
    rows.append([KeyboardButton(text="◀️ Назад")])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True, one_time_keyboard=True)

async def admin_edit_options_kb(gift_key: str) -> ReplyKeyboardMarkup:
    sale = await db_get_sale(gift_key)
    rows = [
        [KeyboardButton(text="✏️ Изменить название")],
        [KeyboardButton(text="💰 Изменить цену")],
        [KeyboardButton(text="❌ Убрать скидку")] if sale else [KeyboardButton(text="🔥 Поставить скидку")],
        [KeyboardButton(text="◀️ Назад")],
    ]
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True, one_time_keyboard=True)

# ==================== ИНИЦИАЛИЗАЦИЯ ====================
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
logging.basicConfig(level=logging.INFO)

# ==================== УТИЛИТЫ ====================

async def send_gift_sticker(message: Message, gift: dict):
    sticker_id = gift.get("sticker_id")
    if sticker_id:
        try:
            await message.answer_sticker(sticker_id)
        except Exception:
            pass

async def tg_send_gift(user_id: int, gift_id: str, text: str = None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendGift"
    params = {"user_id": user_id, "gift_id": gift_id}
    if text:
        params["text"] = text
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=params) as resp:
            result = await resp.json()
            if not result.get("ok"):
                error_code = result.get("error_code", "?")
                description = result.get("description", "Unknown error")
                logging.error(f"sendGift failed: user_id={user_id}, gift_id={gift_id}, code={error_code}, desc={description}")
                raise Exception(f"[{error_code}] {description}")
            logging.info(f"sendGift OK: user_id={user_id}, gift_id={gift_id}")
            return result

# ==================== ХЭНДЛЕРЫ ====================

@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await db_add_user(message.from_user.id)

    if maintenance_mode and message.from_user.id != OWNER_ID:
        await message.answer(
            "🛠 <b>Бот на обслуживании</b>\n\nСкоро вернёмся! ⏳",
            parse_mode="HTML"
        )
        return

    args = message.text.split()
    if len(args) > 1 and args[1].startswith("gift_"):
        token = args[1][5:]
        pending = await db_pop_pending_gift(token)
        if pending:
            buyer_id = pending["buyer_id"]
            gift_key = pending["gift_key"]
            msg_text = pending.get("message_text", "")
            gift = ALL_GIFTS[gift_key]
            friend_id = message.from_user.id

            if friend_id == buyer_id:
                await message.answer(
                    "😅 Нельзя отправить подарок самому себе!\nИспользуй '🎀 Купить себе'.",
                    reply_markup=main_reply_kb(message.from_user.id)
                )
                return

            try:
                await tg_send_gift(user_id=friend_id, gift_id=str(gift["id"]), text=msg_text or None)
                price = await get_gift_price(gift_key)
                await db_add_history(buyer_id, {
                    "gift_key": gift_key, "gift_name": gift["name"], "emoji": gift["emoji"],
                    "target": "friend", "friend_id": friend_id,
                    "stars": price,
                    "date": datetime.now().strftime("%d.%m.%Y %H:%M")
                })
                await message.answer(
                    f"🎁 Тебе отправили подарок: {gift['emoji']} <b>{gift['name']}</b>!\n"
                    f"{'💬 ' + msg_text if msg_text else ''}",
                    parse_mode="HTML",
                    reply_markup=main_reply_kb(message.from_user.id)
                )
                try:
                    await bot.send_message(
                        buyer_id,
                        f"✅ Подарок {gift['emoji']} <b>{gift['name']}</b> успешно доставлен другу!",
                        parse_mode="HTML"
                    )
                except (TelegramForbiddenError, Exception):
                    pass
            except Exception as e:
                await message.answer(f"⚠️ Ошибка при получении подарка: {e}", reply_markup=main_reply_kb(message.from_user.id))
            return

    await state.clear()
    global BANNER_FILE_ID
    welcome_text = (
        "👋 <b>Привет!</b>\n\n"
        "Здесь ты можешь отправить удалённый подарок 🎁\n"
        "который уже недоступен в магазине Telegram,\n"
        "и подарить его <b>себе</b> или своему <b>другу</b>.\n\n"
        " <a href='https://t.me/lmao_owner/c/4'>Нажми, чтобы увидеть пример</a>\n\n"
    )
    try:
        await message.answer_photo(
            photo=BANNER_FILE_ID,
            caption=welcome_text,
            parse_mode="HTML",
            reply_markup=main_reply_kb(message.from_user.id)
        )
    except Exception as e:
        logging.error(f"Ошибка отправки баннера: {e}")
        await message.answer(welcome_text, parse_mode="HTML", reply_markup=main_reply_kb(message.from_user.id))

# ==================== REPLY КНОПКИ ====================

@dp.message(F.text == "🎁 Купить подарок")
async def reply_buy_gift(message: Message, state: FSMContext):
    if maintenance_mode and message.from_user.id != OWNER_ID:
        await message.answer("🛠 <b>Бот на обслуживании, скоро вернёмся!</b>", parse_mode="HTML")
        return
    await state.clear()
    await state.set_state(GiftStates.selecting_gift_reply)
    await state.update_data(preselected_target=None)
    await message.answer("🎁 Выбери подарок:", reply_markup=await gifts_list_reply_kb("any"))

@dp.message(F.text == "🎄 Отдельные подарки")
async def reply_seasonal_gifts(message: Message, state: FSMContext):
    if maintenance_mode and message.from_user.id != OWNER_ID:
        await message.answer("🛠 <b>Бот на обслуживании, скоро вернёмся!</b>", parse_mode="HTML")
        return
    await state.clear()
    await state.set_state(GiftStates.selecting_seasonal_gift_reply)
    await state.update_data(preselected_target=None, gift_source="seasonal")
    await message.answer("🎄 Выбери сезонный подарок:", reply_markup=await seasonal_gifts_list_reply_kb("any"))

@dp.message(GiftStates.selecting_seasonal_gift_reply)
async def reply_seasonal_gift_selected(message: Message, state: FSMContext):
    if message.text == "◀️ Назад":
        await state.clear()
        await message.answer("◀️", reply_markup=main_reply_kb(message.from_user.id))
        return
    mapping = await gift_keys_by_text()
    gift_key = mapping.get(message.text)
    if not gift_key:
        await message.answer("❓ Выбери подарок из списка.", reply_markup=await seasonal_gifts_list_reply_kb("any"))
        return
    data = await state.get_data()
    await after_gift_chosen(message, state, gift_key, data.get("preselected_target"))

@dp.message(F.text == "📜 История")
async def reply_history(message: Message):
    records = await db_get_history(message.from_user.id)
    if not records:
        await message.answer("📭 У тебя пока нет истории подарков.")
        return
    text = "📜 <b>История твоих подарков:</b>\n\n"
    for r in records:
        recipient = "Себе" if r['target'] == 'self' else "Другу"
        text += (
            f"{r['emoji']} <b>{r['gift_name']}</b> — {recipient}\n"
            f"   💰 {r['stars']} ⭐ • {r['date']}\n\n"
        )
    await message.answer(text, parse_mode="HTML")

@dp.message(F.text == "❌ Отмена")
async def reply_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(".", reply_markup=main_reply_kb(message.from_user.id))

# ==================== ВЫБОР ПОДАРКА ====================

async def after_gift_chosen(message: Message, state: FSMContext, gift_key: str, preselected: str):
    gift = ALL_GIFTS[gift_key]
    await state.update_data(gift_key=gift_key)
    await send_gift_sticker(message, gift)

    price_text = await get_price_display(gift_key)

    if preselected == "self":
        await state.update_data(target="self")
        await state.set_state(GiftStates.ask_anon)
        await message.answer(
            f"✅ Вы выбрали: <b>{gift['name']}</b>\n💰 Цена: {price_text}\n\n"
            f"🎭 <b>Как отправить подарок себе?</b>\n\n"
            f"• <b>Анонимно</b> — подарок без подписи отправителя\n"
            f"• <b>От своего имени</b> — в комментарии будет твоё имя",
            parse_mode="HTML",
            reply_markup=anon_choice_kb()
        )
    elif preselected == "friend":
        await state.update_data(target="friend")
        await state.set_state(GiftStates.entering_friend_id)
        await message.answer(
            f"✅ Вы выбрали: {gift['name']}\n💰 Цена: {price_text}\n\n"
            f"⚠️ <b>ВАЖНО перед оплатой!</b>\n"
            f"Друг обязательно должен <b>запустить этого бота</b> (нажать /start) — иначе звёзды спишутся, а подарок не отправится!\n\n"
            f"🔗 Ссылка на бота: <code>t.me/{BOT_USERNAME}</code>\n\n"
            f"🆔 <b>Введите Telegram ID друга:</b>\n\n"
            f"<i>Узнать ID можно через @userinfobot</i>",
            parse_mode="HTML",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="◀️ Назад")]],
                resize_keyboard=True
            )
        )
    else:
        await state.set_state(GiftStates.selecting_whom_reply)
        await message.answer(
            f"✅ Вы выбрали: {gift['name']}\n💰 Цена: {price_text}\n\n📦 Кому отправить подарок?",
            parse_mode="HTML",
            reply_markup=whom_kb()
        )

@dp.message(GiftStates.selecting_gift_reply)
async def reply_gift_selected(message: Message, state: FSMContext):
    if message.text == "◀️ Назад":
        await state.clear()
        await message.answer("◀️", reply_markup=main_reply_kb(message.from_user.id))
        return
    mapping = await gift_keys_by_text()
    gift_key = mapping.get(message.text)
    if not gift_key:
        await message.answer("❓ Выбери подарок из списка.", reply_markup=await gifts_list_reply_kb("any"))
        return
    data = await state.get_data()
    await after_gift_chosen(message, state, gift_key, data.get("preselected_target"))

@dp.message(GiftStates.selecting_whom_reply)
async def reply_whom_selected(message: Message, state: FSMContext):
    if message.text == "◀️ Назад":
        data = await state.get_data()
        if data.get("gift_source") == "seasonal":
            await state.set_state(GiftStates.selecting_seasonal_gift_reply)
            await state.update_data(preselected_target=None)
            await message.answer("🎄 Выбери сезонный подарок:", reply_markup=await seasonal_gifts_list_reply_kb("any"))
        else:
            await state.set_state(GiftStates.selecting_gift_reply)
            await state.update_data(preselected_target=None)
            await message.answer("🎁 Выбери подарок:", reply_markup=await gifts_list_reply_kb("any"))
        return
    data = await state.get_data()
    gift_key = data.get("gift_key")

    if message.text == "👤 Себе":
        await state.update_data(target="self")
        await state.set_state(GiftStates.ask_anon)
        gift = ALL_GIFTS[gift_key]
        price_text = await get_price_display(gift_key)
        await message.answer(
            f"✅ Вы выбрали: <b>{gift['name']}</b>\n💰 Цена: {price_text}\n\n"
            f"🎭 <b>Как отправить подарок себе?</b>\n\n"
            f"• <b>Анонимно</b> — подарок без подписи отправителя\n"
            f"• <b>От своего имени</b> — в комментарии будет твоё имя",
            parse_mode="HTML",
            reply_markup=anon_choice_kb()
        )
    elif message.text == "👥 Другу":
        await state.update_data(target="friend")
        await state.set_state(GiftStates.entering_friend_id)
        await message.answer(
            f"⚠️ <b>ВАЖНО перед оплатой!</b>\n"
            f"Друг обязательно должен <b>запустить этого бота</b> (нажать /start) — иначе звёзды спишутся, а подарок не отправится!\n\n"
            f"🔗 Ссылка на бота: <code>t.me/{BOT_USERNAME}</code>\n\n"
            f"🆔 <b>Введите Telegram ID друга:</b>\n\n"
            f"<i>Узнать ID можно через @userinfobot</i>",
            parse_mode="HTML",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="◀️ Назад")]],
                resize_keyboard=True
            )
        )
    else:
        await message.answer("❓ Нажми одну из кнопок.", reply_markup=whom_kb())

@dp.message(GiftStates.choosing_gift_for_friend)
async def friend_gift_selected(message: Message, state: FSMContext):
    if message.text == "◀️ Назад":
        await state.clear()
        await message.answer("◀️", reply_markup=main_reply_kb(message.from_user.id))
        return
    mapping = await gift_keys_by_text()
    gift_key = mapping.get(message.text)
    if not gift_key:
        await message.answer("❓ Выбери подарок из списка.", reply_markup=await gifts_list_reply_kb("friend"))
        return
    await after_gift_chosen(message, state, gift_key, "friend")

# ==================== ВВОД ID ДРУГА ====================

@dp.message(GiftStates.entering_friend_id)
async def got_friend_id(message: Message, state: FSMContext):
    if message.text == "◀️ Назад":
        data = await state.get_data()
        gift_key = data.get("gift_key")
        if gift_key:
            gift = ALL_GIFTS[gift_key]
            price_text = await get_price_display(gift_key)
            await state.set_state(GiftStates.selecting_whom_reply)
            await message.answer(
                f"✅ Вы выбрали: {gift['name']}\n💰 Цена: {price_text}\n\n📦 Кому отправить подарок?",
                parse_mode="HTML",
                reply_markup=whom_kb()
            )
        else:
            await state.clear()
            await message.answer("◀️", reply_markup=main_reply_kb(message.from_user.id))
        return

    try:
        friend_id = int(message.text.strip())
    except ValueError:
        await message.answer(
            "❗ Введи числовой Telegram ID. Например: <code>123456789</code>\n\n"
            "<i>Узнать ID можно через @userinfobot</i>",
            parse_mode="HTML"
        )
        return

    if friend_id == message.from_user.id:
        await message.answer(
            "😅 Нельзя отправить подарок самому себе!\nВведи ID друга или используй '🎀 Купить себе'."
        )
        return

    # Проверяем что друг запускал бота
    all_users = await db_get_all_users()
    if friend_id not in all_users:
        await message.answer(
            f"❌ <b>Пользователь с ID <code>{friend_id}</code> не найден в боте!</b>\n\n"
            f"Попроси друга сначала запустить бота — нажать /start по ссылке:\n"
            f"👉 <code>t.me/{BOT_USERNAME}</code>\n\n"
            f"После этого введи его ID снова. Без этого шага звёзды пропадут, а подарок не отправится! ⚠️",
            parse_mode="HTML"
        )
        return

    await state.update_data(friend_id=friend_id)
    await state.set_state(GiftStates.ask_anon)
    data = await state.get_data()
    gift_key = data["gift_key"]
    gift = ALL_GIFTS[gift_key]
    price_text = await get_price_display_for_user(gift_key, message.from_user.id)
    await message.answer(
        f"✅ Получатель: <code>{friend_id}</code>\n"
        f"🎁 Подарок: <b>{gift['name']}</b> — {price_text}\n\n"
        f"🎭 <b>Как отправить подарок?</b>\n\n"
        f"• <b>Анонимно</b> — получатель увидит только подарок, без имени отправителя\n"
        f"• <b>От своего имени</b> — в комментарии к подарку появится твоё имя и @username",
        parse_mode="HTML",
        reply_markup=anon_choice_kb()
    )

@dp.message(GiftStates.ask_anon)
async def got_anon_choice(message: Message, state: FSMContext):
    data = await state.get_data()
    gift_key = data.get("gift_key")
    gift = ALL_GIFTS[gift_key]
    target = data.get("target", "self")

    if message.text == "◀️ Назад":
        if target == "friend":
            # Возврат к вводу ID друга
            await state.set_state(GiftStates.entering_friend_id)
            await message.answer(
                f"🆔 <b>Введите Telegram ID друга:</b>\n\n"
                f"<i>Узнать ID можно через @userinfobot</i>",
                parse_mode="HTML",
                reply_markup=ReplyKeyboardMarkup(
                    keyboard=[[KeyboardButton(text="◀️ Назад")]],
                    resize_keyboard=True
                )
            )
        else:
            # Возврат к выбору кому (себе/другу)
            price_text = await get_price_display(gift_key)
            await state.set_state(GiftStates.selecting_whom_reply)
            await message.answer(
                f"✅ Вы выбрали: <b>{gift['name']}</b>\n💰 Цена: {price_text}\n\n📦 Кому отправить подарок?",
                parse_mode="HTML",
                reply_markup=whom_kb()
            )
        return

    if message.text == "🎭 Анонимно":
        await state.update_data(anonymous=True)
        anon_label = "🎭 Анонимно"
    elif message.text == "👤 От своего имени":
        await state.update_data(anonymous=False)
        anon_label = "👤 От своего имени"
    else:
        await message.answer("❓ Нажми одну из кнопок.", reply_markup=anon_choice_kb())
        return

    await state.set_state(GiftStates.ask_comment)
    price_text = await get_price_display_for_user(gift_key, message.from_user.id)
    await message.answer(
        f"✅ {anon_label}\n\n"
        f"🎁 <b>{gift['name']}</b> — {price_text}\n\n"
        f"✏️ Хотите добавить комментарий к подарку?",
        parse_mode="HTML",
        reply_markup=yes_no_kb()
    )

@dp.message(GiftStates.ask_comment, F.text == "✅ Да")
async def ask_comment_yes(message: Message, state: FSMContext):
    await state.set_state(GiftStates.entering_comment)
    await message.answer(
        "📝 Введите комментарий (максимум 200 символов, без премиум эмодзи):",
        reply_markup=ReplyKeyboardRemove()
    )

@dp.message(GiftStates.ask_comment, F.text == "❌ Нет")
async def ask_comment_no(message: Message, state: FSMContext):
    data = await state.get_data()
    # Сохраняем anonymous из предыдущего шага (ask_anon), не перезаписываем
    current_anon = data.get("anonymous", True)
    await state.update_data(message_text="", anonymous=current_anon)
    data = await state.get_data()
    gift_key = data["gift_key"]
    target = data["target"]
    await _show_confirm(message, state, gift_key, target, "")

@dp.message(GiftStates.ask_comment, F.text == "◀️ Назад")
async def ask_comment_back(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("◀️", reply_markup=main_reply_kb(message.from_user.id))

@dp.message(GiftStates.entering_comment)
async def got_comment(message: Message, state: FSMContext):
    comment = message.text[:200] if message.text else ""
    data = await state.get_data()
    # Сохраняем anonymous из предыдущего шага (ask_anon)
    current_anon = data.get("anonymous", False)
    await state.update_data(message_text=comment, anonymous=current_anon)
    data = await state.get_data()
    gift_key = data["gift_key"]
    target = data["target"]
    token = data.get("pending_token")
    if token:
        await db_update_pending_gift_text(token, comment)
    await _show_confirm(message, state, gift_key, target, comment)

async def _show_confirm(message: Message, state: FSMContext, gift_key: str, target: str, comment: str):
    data = await state.get_data()
    gift = ALL_GIFTS[gift_key]
    user_id = message.from_user.id
    price_text = await get_price_display_for_user(gift_key, user_id)
    friend_id = data.get("friend_id")
    is_anon = data.get("anonymous", True)

    if target == "friend" and friend_id:
        anon_line = "🎭 Анонимно" if is_anon else f"👤 От своего имени"
        text = (
            f"🎁 <b>{gift['name']}</b> — {price_text}\n\n"
            f"👥 Получатель: <code>{friend_id}</code>\n"
            f"📤 Отправка: {anon_line}"
        )
        if comment:
            text += f"\n\n💬 Комментарий: <i>{comment}</i>"
        await message.answer(text, parse_mode="HTML", reply_markup=cancel_only_kb())
        await message.answer(
            f"💳 Подарок: <b>{gift['name']}</b>\n💰 Цена: {price_text}",
            reply_markup=await confirm_buy_kb(gift_key, "friend", str(friend_id), user_id),
            parse_mode="HTML"
        )
    else:
        anon_line = "🎭 Анонимно" if is_anon else "👤 От своего имени"
        text = (
            f"🎁 <b>{gift['name']}</b> — {price_text}\n\n"
            f"👤 Получатель: Себе\n"
            f"📤 Отправка: {anon_line}"
        )
        if comment:
            text += f"\n\n💬 Комментарий: <i>{comment}</i>"
        await message.answer(text, parse_mode="HTML", reply_markup=cancel_only_kb())
        await message.answer(
            f"💳 Подарок: <b>{gift['name']}</b>\n💰 Цена: {price_text}",
            reply_markup=await confirm_buy_kb(gift_key, target, "", user_id),
            parse_mode="HTML"
        )

# ==================== INLINE МЕНЮ ====================

@dp.callback_query(F.data == "back_main")
async def back_main(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("🎁 Главное меню:", reply_markup=await main_menu_kb(call.from_user.id))

@dp.callback_query(F.data == "buy_gift")
async def buy_gift(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("🎁 Кому хочешь подарить?", reply_markup=buy_for_whom_kb())

@dp.callback_query(F.data == "gift_history")
async def show_history(call: CallbackQuery):
    records = await db_get_history(call.from_user.id)
    if not records:
        await call.answer("📭 У тебя пока нет истории подарков.", show_alert=True)
        return
    text = "📜 <b>История твоих подарков:</b>\n\n"
    for r in records:
        recipient = "Себе" if r['target'] == 'self' else "Другу"
        text += (
            f"{r['emoji']} <b>{r['gift_name']}</b> — {recipient}\n"
            f"   💰 {r['stars']} ⭐ • {r['date']}\n\n"
        )
    await call.message.edit_text(text, reply_markup=await main_menu_kb(), parse_mode="HTML")

@dp.callback_query(F.data == "buy_for_self")
async def buy_for_self(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(GiftStates.selecting_gift_reply)
    await state.update_data(preselected_target="self")
    await call.message.answer("🎁 Выбери подарок:", reply_markup=await gifts_list_reply_kb("self"))
    await call.answer()

@dp.callback_query(F.data == "buy_for_friend")
async def buy_for_friend(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(GiftStates.selecting_gift_reply)
    await state.update_data(preselected_target="friend")
    await call.message.answer("🎁 Выбери подарок:", reply_markup=await gifts_list_reply_kb("friend"))
    await call.answer()

@dp.callback_query(F.data.startswith("send_anon:"))
async def send_anon(call: CallbackQuery, state: FSMContext):
    _, gift_key, friend_id = call.data.split(":")
    await state.update_data(anonymous=True, message_text="", friend_id=int(friend_id))
    gift = ALL_GIFTS[gift_key]
    price_text = await get_price_display(gift_key)
    await call.message.edit_text(
        f"{gift['emoji']} <b>{gift['name']}</b> — анонимно\n\n"
        f"💰 Цена: {price_text}\n\nПодтверди оплату:",
        reply_markup=await confirm_buy_kb(gift_key, "friend", str(friend_id)),
        parse_mode="HTML"
    )
    await call.message.answer(".", reply_markup=cancel_only_kb())
    await call.answer()

@dp.callback_query(F.data.startswith("send_text:"))
async def send_text_choice(call: CallbackQuery, state: FSMContext):
    _, gift_key, friend_id = call.data.split(":")
    await state.update_data(anonymous=False, gift_key=gift_key, friend_id=int(friend_id))
    await state.set_state(GiftStates.ask_comment)
    gift = ALL_GIFTS[gift_key]
    price_text = await get_price_display(gift_key)
    await call.message.edit_text(
        f"{gift['emoji']} <b>{gift['name']}</b>\n\n💰 Цена: {price_text}",
        parse_mode="HTML"
    )
    await call.message.answer("✏️ Хотите добавить комментарий к подарку?", reply_markup=yes_no_kb())
    await call.answer()

# ==================== ОПЛАТА ====================

@dp.callback_query(F.data.startswith("pay:"))
async def process_payment(call: CallbackQuery, state: FSMContext):
    parts = call.data.split(":")
    gift_key = parts[1]
    target = parts[2]
    extra = parts[3] if len(parts) > 3 else ""

    gift = ALL_GIFTS[gift_key]
    data = await state.get_data()
    user_id = call.from_user.id
    price = await get_gift_price_for_user(gift_key, user_id)

    # Финальная проверка: если подарок для друга — убеждаемся что он есть в базе
    if target == "friend" and extra and extra.isdigit():
        friend_id_check = int(extra)
        all_users = await db_get_all_users()
        if friend_id_check not in all_users:
            await call.answer(
                f"❌ Друг с ID {friend_id_check} не запускал бота!\n"
                f"Попроси его нажать /start в t.me/{BOT_USERNAME}, затем попробуй снова.",
                show_alert=True
            )
            return

    promo = await db_get_user_promo(user_id)
    used_promo = promo["code"] if promo else None

    pay_token = secrets.token_hex(8)

    try:
        invoice_msg = await bot.send_invoice(
            chat_id=user_id,
            title=f"{gift['emoji']} {gift['name']}",
            description="Подарок для себя" if target == "self" else "Подарок для друга",
            payload=pay_token,
            currency="XTR",
            prices=[LabeledPrice(label=gift['name'], amount=price)],
            provider_token="",
        )
        await db_set_pending_payment(pay_token, {
            "gift_key": gift_key,
            "target": target,
            "extra": extra,
            "anonymous": data.get("anonymous", True),
            "message_text": data.get("message_text", ""),
            "buyer_id": user_id,
            "used_promo": used_promo,
            "invoice_msg_id": invoice_msg.message_id,
        })
        await call.answer()
    except Exception as e:
        await call.answer(f"Ошибка: {e}", show_alert=True)

@dp.pre_checkout_query()
async def pre_checkout(pre_checkout_query: PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)

@dp.message(F.successful_payment)
async def successful_payment(message: Message, state: FSMContext):
    payment = message.successful_payment
    pay_token = payment.invoice_payload

    payload = await db_pop_pending_payment(pay_token)
    if not payload:
        await message.answer(
            "⚠️ Оплата прошла, но данные заказа не найдены.\n"
            "Напиши администратору — он отправит подарок вручную.",
            reply_markup=main_reply_kb(message.from_user.id)
        )
        try:
            await bot.send_message(
                OWNER_ID,
                f"🚨 <b>ПОТЕРЯН ЗАКАЗ!</b>\n\n"
                f"👤 Покупатель: <code>{message.from_user.id}</code>\n"
                f"💳 Токен: <code>{pay_token}</code>\n"
                f"⭐ Сумма: {payment.total_amount} Stars\n"
                f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
                f"<i>Данные заказа не найдены в БД. Требуется ручная отправка!</i>",
                parse_mode="HTML"
            )
        except Exception:
            pass
        await state.clear()
        return

    # Удаляем сообщение с инвойсом чтобы не дублировалось
    invoice_msg_id = payload.get("invoice_msg_id")
    if invoice_msg_id:
        try:
            await bot.delete_message(message.chat.id, invoice_msg_id)
        except Exception:
            pass

    gift_key = payload["gift_key"]
    target = payload["target"]
    extra = payload.get("extra", "")
    msg_text = payload.get("message_text", "")
    buyer_id = payload.get("buyer_id", message.from_user.id)
    used_promo = payload.get("used_promo")

    if used_promo:
        await db_promo_use(used_promo, buyer_id)
    await db_delete_user_promo(buyer_id)

    gift = ALL_GIFTS.get(gift_key)
    if not gift:
        await message.answer(
            "⚠️ Оплата прошла, но подарок не найден в базе. Обратись к администратору.",
            reply_markup=main_reply_kb(message.from_user.id)
        )
        try:
            await bot.send_message(
                OWNER_ID,
                f"🚨 <b>ОШИБКА: неизвестный gift_key!</b>\n\n"
                f"👤 Покупатель: <code>{buyer_id}</code>\n"
                f"🎁 gift_key: <code>{gift_key}</code>\n"
                f"⭐ Сумма: {payment.total_amount} Stars\n"
                f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}",
                parse_mode="HTML"
            )
        except Exception:
            pass
        await state.clear()
        return

    gift_telegram_id = str(gift["id"])
    price = payment.total_amount

    # Определяем получателя
    if target == "self":
        recipient_id = buyer_id
        recipient_label = "себе"
    elif target == "friend" and extra and extra.isdigit():
        recipient_id = int(extra)
        recipient_label = f"другу <code>{recipient_id}</code>"
    else:
        # Нет ID получателя — уведомляем владельца и пользователя
        await message.answer(
            "⚠️ Оплата прошла, но ID получателя не найден.\n"
            "Администратор уже уведомлён и отправит подарок вручную.",
            reply_markup=main_reply_kb(message.from_user.id)
        )
        try:
            await bot.send_message(
                OWNER_ID,
                f"🚨 <b>НЕТ ID ПОЛУЧАТЕЛЯ!</b>\n\n"
                f"👤 Покупатель: <code>{buyer_id}</code>\n"
                f"🎁 Подарок: {gift['emoji']} {gift['name']}\n"
                f"🎯 target: <code>{target}</code>, extra: <code>{extra}</code>\n"
                f"⭐ Оплачено: {price} Stars\n"
                f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
                f"<i>Отправь подарок вручную через 🎁 Отправить подарок!</i>",
                parse_mode="HTML"
            )
        except Exception:
            pass
        await state.clear()
        return

    # Отправляем подарок с повторными попытками
    last_error = None
    for attempt in range(3):
        try:
            await tg_send_gift(user_id=recipient_id, gift_id=gift_telegram_id, text=msg_text or None)
            last_error = None
            break
        except Exception as e:
            last_error = e
            logging.warning(f"Попытка {attempt+1}/3 отправки подарка не удалась: {e}")
            if attempt < 2:
                await asyncio.sleep(2)

    if last_error:
        # Все попытки провалились — сохраняем в историю как неудачную и уведомляем владельца
        logging.error(f"Не удалось отправить подарок после 3 попыток: {last_error}")
        await message.answer(
            f"⚠️ Оплата прошла успешно ({price} ⭐), но произошла ошибка при отправке подарка.\n"
            f"Администратор уже уведомлён и отправит подарок вручную в ближайшее время.",
            reply_markup=main_reply_kb(message.from_user.id)
        )
        try:
            await bot.send_message(
                OWNER_ID,
                f"🚨 <b>ОШИБКА ОТПРАВКИ ПОДАРКА!</b>\n\n"
                f"🎁 {gift['emoji']} {gift['name']}\n"
                f"👤 Покупатель: <code>{buyer_id}</code>\n"
                f"🎯 Получатель: {recipient_label}\n"
                f"⭐ Оплачено: {price} Stars\n"
                f"❌ Ошибка: <code>{last_error}</code>\n"
                f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
                f"<b>Отправь подарок вручную через 🎁 Отправить подарок!</b>\n"
                f"ID получателя: <code>{recipient_id}</code>",
                parse_mode="HTML"
            )
        except Exception:
            pass
        await state.clear()
        return

    # Успех — записываем историю
    await db_add_history(buyer_id, {
        "gift_key": gift_key, "gift_name": gift["name"], "emoji": gift["emoji"],
        "target": target, "friend_id": recipient_id if target == "friend" else None,
        "stars": price, "date": datetime.now().strftime("%d.%m.%Y %H:%M")
    })

    # Сообщение покупателю
    if target == "self":
        confirm = f"🎉 Подарок {gift['emoji']} <b>{gift['name']}</b> отправлен тебе!\n✨ Он появится в твоём профиле."
    else:
        is_anon = payload.get("anonymous", True)
        anon_note = "🎭 анонимно" if is_anon else "👤 от твоего имени"
        confirm = f"🎉 Подарок {gift['emoji']} <b>{gift['name']}</b> отправлен другу {anon_note}!\n✨ Он появится в его профиле."
    if msg_text:
        confirm += f"\n💬 Комментарий: <i>{msg_text}</i>"
    await message.answer(confirm, parse_mode="HTML", reply_markup=main_reply_kb(message.from_user.id))

    # Уведомляем друга
    if target == "friend":
        try:
            is_anon = payload.get("anonymous", True)
            if is_anon:
                # Анонимно — имя не упоминаем вообще
                notif = (
                    f"🎁 Тебе прислали подарок: {gift['emoji']} <b>{gift['name']}</b>!\n"
                    f"✨ Он уже в твоём профиле Telegram.\n\n"
                    f"🎭 <i>Отправитель пожелал остаться анонимным</i>"
                )
                if msg_text:
                    notif += f"\n💬 <i>{msg_text}</i>"
            else:
                # От своего имени — добавляем имя и username в комментарий
                sender = message.from_user
                sender_mention = f"<a href='tg://user?id={buyer_id}'>{sender.full_name}</a>"
                if sender.username:
                    sender_mention += f" (@{sender.username})"
                notif = (
                    f"🎁 Тебе прислали подарок: {gift['emoji']} <b>{gift['name']}</b>!\n"
                    f"✨ Он уже в твоём профиле Telegram.\n\n"
                    f"👤 От: {sender_mention}"
                )
                if msg_text:
                    notif += f"\n💬 <i>{msg_text}</i>"
            await bot.send_message(recipient_id, notif, parse_mode="HTML")
        except TelegramForbiddenError:
            pass  # Получатель заблокировал бота — подарок всё равно доставлен через Telegram
        except Exception:
            pass

    # Уведомление владельцу о продаже
    commission = price - gift["real_price"]
    try:
        await bot.send_message(
            OWNER_ID,
            f"💰 <b>Новая продажа!</b>\n\n"
            f"{gift['emoji']} {gift['name']}\n"
            f"👤 Покупатель: <code>{buyer_id}</code>\n"
            f"🎯 Получатель: {'себе' if target == 'self' else recipient_label}\n"
            f"⭐ Оплачено: {price} Stars\n"
            f"💎 Комиссия: {commission} Stars\n"
            f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}",
            parse_mode="HTML"
        )
    except Exception:
        pass

    await state.clear()

# ==================== АДМИН ПАНЕЛЬ ====================

@dp.message(F.text == "⚙️ Админ панель")
async def admin_panel(message: Message, state: FSMContext):
    if message.from_user.id != OWNER_ID:
        return
    await state.clear()
    await message.answer(
        "⚙️ <b>Админ панель</b>\n\nВыбери действие:",
        parse_mode="HTML",
        reply_markup=admin_main_kb()
    )

@dp.message(F.text == "◀️ Главное меню")
async def admin_back_main(message: Message, state: FSMContext):
    if message.from_user.id != OWNER_ID:
        return
    await state.clear()
    await message.answer("👋 Главное меню", reply_markup=main_reply_kb(message.from_user.id))

# --- Статистика ---

@dp.message(F.text == "📊 Статистика")
async def admin_stats(message: Message):
    if message.from_user.id != OWNER_ID:
        return

    total_users = await db_count_users()
    all_hist = await db_all_history()
    total_purchases = len(all_hist)
    total_stars = sum(r["stars"] for r in all_hist)
    commission = sum(
        (r["stars"] - ALL_GIFTS.get(r["gift_key"], {}).get("real_price", r["stars"]))
        for r in all_hist
        if r["gift_key"] in ALL_GIFTS
    )
    gift_counter = Counter(r["gift_key"] for r in all_hist)
    top = gift_counter.most_common(3)
    top_text = ""
    for i, (gk, cnt) in enumerate(top, 1):
        g = ALL_GIFTS.get(gk, {})
        top_text += f"  {i}. {g.get('emoji','?')} {g.get('name', gk)} — {cnt} шт.\n"

    pending_count = await db_count_pending_gifts()
    all_sales = await db_get_all_sales()

    text = (
        f"📊 <b>Статистика бота</b>\n\n"
        f"👥 Всего юзеров: <b>{total_users}</b>\n"
        f"🛒 Всего покупок: <b>{total_purchases}</b>\n"
        f"⭐ Выручка: <b>{total_stars} Stars</b>\n"
        f"💎 Комиссия: <b>{commission} Stars</b>\n"
        f"⏳ Ждут доставки: <b>{pending_count}</b>\n"
        f"🔥 Активных скидок: <b>{len(all_sales)}</b>\n"
    )
    if top_text:
        text += f"\n🏆 <b>Топ подарков:</b>\n{top_text}"

    await message.answer(text, parse_mode="HTML", reply_markup=admin_main_kb())

# --- Рассылка ---

@dp.message(F.text == "📢 Рассылка")
async def admin_broadcast_start(message: Message, state: FSMContext):
    if message.from_user.id != OWNER_ID:
        return
    total_users = await db_count_users()
    await state.set_state(GiftStates.admin_broadcast)
    await message.answer(
        f"📢 <b>Рассылка</b>\n\n"
        f"Юзеров в базе: <b>{total_users}</b>\n\n"
        f"Напиши текст сообщения. Поддерживается HTML:\n"
        f"<code>&lt;b&gt;жирный&lt;/b&gt;</code>, <code>&lt;i&gt;курсив&lt;/i&gt;</code>\n\n"
        f"Нажми ◀️ Назад для отмены.",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="◀️ Назад")]],
            resize_keyboard=True
        )
    )

@dp.message(GiftStates.admin_broadcast)
async def admin_broadcast_send(message: Message, state: FSMContext):
    if message.from_user.id != OWNER_ID:
        return
    if message.text == "◀️ Назад":
        await state.clear()
        await message.answer("◀️", reply_markup=admin_main_kb())
        return

    text = message.text
    all_users = await db_get_all_users()
    total = len(all_users)
    sent = 0
    failed = 0
    status_msg = await message.answer(f"⏳ Отправляю... 0/{total}")

    blocked = 0
    for i, user_id in enumerate(all_users):
        try:
            await bot.send_message(user_id, text, parse_mode="HTML")
            sent += 1
        except TelegramForbiddenError:
            # Пользователь заблокировал бота — удаляем из БД
            await db_remove_user(user_id)
            failed += 1
            blocked += 1
        except Exception:
            failed += 1
        if (i + 1) % 20 == 0:
            try:
                await status_msg.edit_text(f"⏳ Отправляю... {i+1}/{total}")
            except Exception:
                pass
        await asyncio.sleep(0.05)

    await state.clear()
    blocked_line = f"\n🚫 Заблокировали бота: {blocked} (удалены из БД)" if blocked else ""
    await status_msg.edit_text(
        f"✅ <b>Рассылка завершена!</b>\n\n📤 Отправлено: {sent}\n❌ Не доставлено: {failed - blocked}{blocked_line}",
        parse_mode="HTML"
    )
    await message.answer("Что дальше?", reply_markup=admin_main_kb())

# --- Редактирование подарков ---

@dp.message(F.text == "🎁 Редактировать подарки")
async def admin_edit_gifts(message: Message, state: FSMContext):
    if message.from_user.id != OWNER_ID:
        return
    await state.set_state(GiftStates.admin_select_gift)
    await message.answer(
        "🎁 <b>Выбери подарок для редактирования:</b>\n(🔥 = активная скидка)",
        parse_mode="HTML",
        reply_markup=await admin_gifts_kb()
    )

@dp.message(GiftStates.admin_select_gift)
async def admin_gift_selected(message: Message, state: FSMContext):
    if message.from_user.id != OWNER_ID:
        return
    if message.text == "◀️ Назад":
        await state.clear()
        await message.answer("◀️", reply_markup=admin_main_kb())
        return

    found_key = None
    for key, gift in ALL_GIFTS.items():
        if message.text.startswith(f"{gift['emoji']} {gift['name']}"):
            found_key = key
            break

    if not found_key:
        await message.answer("❓ Выбери подарок из списка.", reply_markup=await admin_gifts_kb())
        return

    await state.update_data(editing_gift_key=found_key)
    await state.set_state(GiftStates.admin_edit_field)

    gift = ALL_GIFTS[found_key]
    price_text = await get_price_display(found_key)
    info = f"🎁 <b>{gift['name']}</b>\n\n💰 Цена: {price_text}\n📝 {gift['description']}\n"
    sale = await db_get_sale(found_key)
    if sale:
        info += f"🔥 Скидка: {sale['sale_price']} ⭐ (было {sale['original_price']} ⭐)\n"

    await message.answer(
        info + "\n<b>Что хочешь изменить?</b>",
        parse_mode="HTML",
        reply_markup=await admin_edit_options_kb(found_key)
    )

@dp.message(GiftStates.admin_edit_field)
async def admin_edit_field_chosen(message: Message, state: FSMContext):
    if message.from_user.id != OWNER_ID:
        return
    data = await state.get_data()
    gift_key = data["editing_gift_key"]
    gift = ALL_GIFTS[gift_key]

    if message.text == "◀️ Назад":
        await state.set_state(GiftStates.admin_select_gift)
        await message.answer("🎁 Выбери подарок:", reply_markup=await admin_gifts_kb())
        return

    if message.text == "✏️ Изменить название":
        await state.update_data(edit_action="name")
        await state.set_state(GiftStates.admin_enter_value)
        await message.answer(
            f"✏️ Текущее название: <b>{gift['name']}</b>\n\nВведи новое название:",
            parse_mode="HTML",
            reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="◀️ Назад")]], resize_keyboard=True)
        )

    elif message.text == "💰 Изменить цену":
        await state.update_data(edit_action="price")
        await state.set_state(GiftStates.admin_enter_value)
        await message.answer(
            f"💰 Текущая цена: <b>{gift['price_stars']} ⭐</b>\n\nВведи новую цену (только число):",
            parse_mode="HTML",
            reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="◀️ Назад")]], resize_keyboard=True)
        )

    elif message.text == "🔥 Поставить скидку":
        await state.update_data(edit_action="sale")
        await state.set_state(GiftStates.admin_enter_sale_price)
        await message.answer(
            f"🔥 <b>Скидка на {gift['name']}</b>\n\n"
            f"Текущая цена: <b>{gift['price_stars']} ⭐</b>\n\n"
            f"Введи цену СО скидкой (число, меньше {gift['price_stars']}):",
            parse_mode="HTML",
            reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="◀️ Назад")]], resize_keyboard=True)
        )

    elif message.text == "❌ Убрать скидку":
        await db_remove_sale(gift_key)
        await message.answer(
            f"✅ Скидка на <b>{gift['name']}</b> убрана!",
            parse_mode="HTML",
            reply_markup=await admin_edit_options_kb(gift_key)
        )

    else:
        await message.answer("❓ Выбери действие.", reply_markup=await admin_edit_options_kb(gift_key))

@dp.message(GiftStates.admin_enter_value)
async def admin_enter_value(message: Message, state: FSMContext):
    if message.from_user.id != OWNER_ID:
        return
    data = await state.get_data()
    gift_key = data["editing_gift_key"]

    if message.text == "◀️ Назад":
        await state.set_state(GiftStates.admin_edit_field)
        await message.answer("Что изменить?", reply_markup=await admin_edit_options_kb(gift_key))
        return

    action = data["edit_action"]
    gift = ALL_GIFTS[gift_key]

    if action == "name":
        new_name = message.text.strip()
        if len(new_name) < 2 or len(new_name) > 50:
            await message.answer("❗ Название: от 2 до 50 символов. Попробуй ещё раз:")
            return
        old_name = gift["name"]
        ALL_GIFTS[gift_key]["name"] = new_name
        if gift_key in GIFTS:
            GIFTS[gift_key]["name"] = new_name
        elif gift_key in SEASONAL_GIFTS:
            SEASONAL_GIFTS[gift_key]["name"] = new_name
        await state.set_state(GiftStates.admin_edit_field)
        await message.answer(
            f"✅ Название изменено!\n<s>{old_name}</s> → <b>{new_name}</b>",
            parse_mode="HTML",
            reply_markup=await admin_edit_options_kb(gift_key)
        )

    elif action == "price":
        try:
            new_price = int(message.text.strip())
            if new_price < 1 or new_price > 10000:
                raise ValueError
        except ValueError:
            await message.answer("❗ Введи корректное число (от 1 до 10000):")
            return
        old_price = gift["price_stars"]
        ALL_GIFTS[gift_key]["price_stars"] = new_price
        if gift_key in GIFTS:
            GIFTS[gift_key]["price_stars"] = new_price
        elif gift_key in SEASONAL_GIFTS:
            SEASONAL_GIFTS[gift_key]["price_stars"] = new_price
        await db_remove_sale(gift_key)
        await state.set_state(GiftStates.admin_edit_field)
        await message.answer(
            f"✅ Цена изменена!\n<s>{old_price} ⭐</s> → <b>{new_price} ⭐</b>",
            parse_mode="HTML",
            reply_markup=await admin_edit_options_kb(gift_key)
        )

@dp.message(GiftStates.admin_enter_sale_price)
async def admin_enter_sale_price(message: Message, state: FSMContext):
    if message.from_user.id != OWNER_ID:
        return
    data = await state.get_data()
    gift_key = data["editing_gift_key"]

    if message.text == "◀️ Назад":
        await state.set_state(GiftStates.admin_edit_field)
        await message.answer("Что изменить?", reply_markup=await admin_edit_options_kb(gift_key))
        return

    gift = ALL_GIFTS[gift_key]
    orig_price = gift["price_stars"]

    try:
        sale_price = int(message.text.strip())
        if sale_price < 1 or sale_price >= orig_price:
            await message.answer(
                f"❗ Цена со скидкой должна быть меньше {orig_price} ⭐ и больше 0.\nПопробуй ещё раз:"
            )
            return
    except ValueError:
        await message.answer("❗ Введи число. Например: 45")
        return

    await db_set_sale(gift_key, sale_price, orig_price)
    await state.set_state(GiftStates.admin_edit_field)
    await message.answer(
        f"🔥 <b>Скидка активирована!</b>\n\n"
        f"{gift['emoji']} {gift['name']}\n"
        f"Новая цена: <b>{sale_price} ⭐</b>  <s>{orig_price} ⭐</s>\n\n"
        f"Покупатели видят зачёркнутую старую цену 👆",
        parse_mode="HTML",
        reply_markup=await admin_edit_options_kb(gift_key)
    )

# ==================== ПРОМОКОД (ПОЛЬЗОВАТЕЛИ) ====================

@dp.message(F.text == "🎟️ Промокод")
async def reply_enter_promo(message: Message, state: FSMContext):
    if maintenance_mode and message.from_user.id != OWNER_ID:
        await message.answer("🛠 <b>Бот на обслуживании, скоро вернёмся!</b>", parse_mode="HTML")
        return
    user_id = message.from_user.id
    promo = await db_get_user_promo(user_id)
    if promo:
        await message.answer(
            f"✅ <b>У тебя уже активен промокод!</b>\n\n"
            f"🎟️ <code>{promo['code']}</code>\n"
            f"💰 Скидка: <b>-{promo['discount']} ⭐</b> на следующую покупку",
            parse_mode="HTML",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="❌ Сбросить промокод")],
                    [KeyboardButton(text="◀️ Главное меню")],
                ],
                resize_keyboard=True, one_time_keyboard=True
            )
        )
        await state.set_state(GiftStates.entering_promo)
        await state.update_data(has_active_promo=True)
        return
    await state.set_state(GiftStates.entering_promo)
    await state.update_data(has_active_promo=False)
    await message.answer(
        "🎟️ <b>Введите промокод:</b>",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="◀️ Главное меню")]],
            resize_keyboard=True, one_time_keyboard=True
        )
    )

@dp.callback_query(F.data == "enter_promo")
async def cb_enter_promo(call: CallbackQuery, state: FSMContext):
    if maintenance_mode and call.from_user.id != OWNER_ID:
        await call.answer("🛠 Бот на обслуживании!", show_alert=True)
        return
    await state.set_state(GiftStates.entering_promo)
    await call.message.answer(
        "🎟️ <b>Введите промокод:</b>\n\nНапример: <code>-10starbotused</code>",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="❌ Отмена")]],
            resize_keyboard=True, one_time_keyboard=True
        )
    )
    await call.answer()

@dp.message(GiftStates.entering_promo)
async def handle_promo_input(message: Message, state: FSMContext):
    user_id = message.from_user.id

    if message.text in ("◀️ Главное меню", "❌ Отмена"):
        await state.clear()
        await message.answer("◀️", reply_markup=main_reply_kb(user_id))
        return

    if message.text == "❌ Сбросить промокод":
        await db_delete_user_promo(user_id)
        await state.clear()
        await message.answer(
            "🗑️ <b>Промокод сброшен.</b>",
            parse_mode="HTML",
            reply_markup=main_reply_kb(user_id)
        )
        return

    data = await state.get_data()
    if data.get("has_active_promo"):
        await state.clear()
        await message.answer("◀️", reply_markup=main_reply_kb(user_id))
        return

    code = message.text.strip()
    promo = await db_get_promo(code)

    if not promo:
        await message.answer(
            "❌ <b>Промокод не найден.</b>\n\nПроверь правильность ввода и попробуй ещё раз:",
            parse_mode="HTML"
        )
        return

    if datetime.now() > promo["expires_at"]:
        await db_delete_promo(code)
        await state.clear()
        await message.answer(
            "⌛ <b>Срок действия этого промокода истёк.</b>",
            parse_mode="HTML",
            reply_markup=main_reply_kb(user_id)
        )
        return

    if user_id in promo.get("used_by", set()):
        await state.clear()
        await message.answer(
            "⚠️ <b>Ты уже использовал этот промокод.</b>",
            parse_mode="HTML",
            reply_markup=main_reply_kb(user_id)
        )
        return

    if promo["activations_left"] <= 0:
        await state.clear()
        await message.answer(
            "❌ <b>Этот промокод больше не активен.</b>",
            parse_mode="HTML",
            reply_markup=main_reply_kb(user_id)
        )
        return

    remaining = promo["expires_at"] - datetime.now()
    rem_hours = int(remaining.total_seconds() // 3600)
    rem_mins = int((remaining.total_seconds() % 3600) // 60)
    if rem_hours >= 24:
        time_str = f"{rem_hours // 24} дн. {rem_hours % 24} ч."
    elif rem_hours > 0:
        time_str = f"{rem_hours} ч. {rem_mins} мин."
    else:
        time_str = f"{rem_mins} мин."

    await db_set_user_promo(user_id, code, promo["discount_stars"], promo.get("gift_key"))
    await state.clear()
    await message.answer(
        f"✅ <b>Промокод активирован!</b>\n\n"
        f"🎟️ <code>{code}</code>\n"
        f"💰 Скидка: <b>-{promo['discount_stars']} ⭐</b> на следующую покупку\n"
        f"⏳ Истекает через: <b>{time_str}</b>\n\n"
        f"Скидка применится автоматически при оплате!",
        parse_mode="HTML",
        reply_markup=main_reply_kb(user_id)
    )

# ==================== РЕЖИМ ОБСЛУЖИВАНИЯ ====================

@dp.message(F.text.in_({"🟢 Вкл. обслуживание", "🔴 Выкл. обслуживание"}))
async def toggle_maintenance(message: Message):
    global maintenance_mode
    if message.from_user.id != OWNER_ID:
        return
    maintenance_mode = not maintenance_mode
    await db_set_setting("maintenance_mode", "1" if maintenance_mode else "0")
    status = "🔴 ВКЛЮЧЁН" if maintenance_mode else "🟢 ВЫКЛЮЧЕН"
    await message.answer(
        f"🛠 <b>Режим обслуживания {status}</b>\n\n"
        + ("Пользователи видят сообщение об обслуживании." if maintenance_mode else "Бот работает в обычном режиме."),
        parse_mode="HTML",
        reply_markup=admin_main_kb()
    )

# ==================== АДМИН — ПРОМОКОДЫ ====================

@dp.message(F.text == "🎟️ Промокоды")
async def admin_promos_menu(message: Message, state: FSMContext):
    if message.from_user.id != OWNER_ID:
        return
    await state.clear()

    all_promos = await db_get_all_promos()
    # Чистим истёкшие
    for code, p in list(all_promos.items()):
        if datetime.now() > p["expires_at"]:
            await db_delete_promo(code)
            del all_promos[code]

    if all_promos:
        lines = []
        for code, p in all_promos.items():
            remaining = p["expires_at"] - datetime.now()
            rem_h = int(remaining.total_seconds() // 3600)
            rem_m = int((remaining.total_seconds() % 3600) // 60)
            if rem_h >= 24:
                time_str = f"{rem_h // 24}д {rem_h % 24}ч"
            elif rem_h > 0:
                time_str = f"{rem_h}ч {rem_m}мин"
            else:
                time_str = f"{rem_m}мин"
            gift_name = ALL_GIFTS[p['gift_key']]['name'] if p.get('gift_key') else 'все подарки'
            lines.append(
                f"🎟️ <code>{code}</code>\n"
                f"   💰 -{p['discount_stars']} ⭐ | 🎁 {gift_name} | 🔢 {p['activations_left']}/{p['total_activations']} | ⏳ {time_str}"
            )
        promos_text = "\n\n".join(lines)
    else:
        promos_text = "Нет активных промокодов."

    await message.answer(
        f"🎟️ <b>Управление промокодами</b>\n\n{promos_text}",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="➕ Создать промокод")],
                [KeyboardButton(text="🗑️ Удалить промокод")],
                [KeyboardButton(text="◀️ Назад")],
            ],
            resize_keyboard=True
        )
    )

@dp.message(F.text == "➕ Создать промокод")
async def admin_create_promo_start(message: Message, state: FSMContext):
    if message.from_user.id != OWNER_ID:
        return
    await state.set_state(GiftStates.admin_promo_name)
    await message.answer(
        "✏️ <b>Введите название промокода:</b>\n\nНапример: <code>-10starbotused</code>",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="◀️ Назад")]],
            resize_keyboard=True
        )
    )

@dp.message(GiftStates.admin_promo_name)
async def admin_promo_got_name(message: Message, state: FSMContext):
    if message.from_user.id != OWNER_ID:
        return
    if message.text == "◀️ Назад":
        await state.clear()
        await message.answer("◀️", reply_markup=admin_main_kb())
        return

    data = await state.get_data()

    if data.get("delete_mode"):
        code = message.text.strip()
        all_promos = await db_get_all_promos()
        if code in all_promos:
            await db_delete_promo(code)
            await state.clear()
            await message.answer(
                f"🗑️ <b>Промокод <code>{code}</code> удалён.</b>",
                parse_mode="HTML",
                reply_markup=admin_main_kb()
            )
        else:
            await message.answer("❓ Такого промокода нет. Выбери из списка или нажми ◀️ Назад.")
        return

    code = message.text.strip()
    if len(code) < 2 or len(code) > 32 or " " in code:
        await message.answer("❗ Название от 2 до 32 символов, без пробелов. Попробуй ещё раз:")
        return

    await state.update_data(promo_code=code)
    await state.set_state(GiftStates.admin_promo_discount)
    await message.answer(
        f"💰 <b>На сколько звёзд скидка?</b>\n\nВведи число (например: <code>10</code>):",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="◀️ Назад")]],
            resize_keyboard=True
        )
    )

@dp.message(GiftStates.admin_promo_discount)
async def admin_promo_got_discount(message: Message, state: FSMContext):
    if message.from_user.id != OWNER_ID:
        return
    if message.text == "◀️ Назад":
        await state.set_state(GiftStates.admin_promo_name)
        await message.answer("✏️ Введите название промокода:")
        return

    try:
        discount = int(message.text.strip())
        if discount < 1 or discount > 9999:
            raise ValueError
    except ValueError:
        await message.answer("❗ Введи корректное число от 1 до 9999:")
        return

    await state.update_data(promo_discount=discount)
    await state.set_state(GiftStates.admin_promo_gift)

    gift_rows = [[KeyboardButton(text="🎁 На все подарки")]]
    for key, gift in ALL_GIFTS.items():
        price = await get_gift_price(key)
        gift_rows.append([KeyboardButton(text=f"{gift['emoji']} {gift['name']} — {price} ⭐")])
    gift_rows.append([KeyboardButton(text="◀️ Назад")])

    await message.answer(
        "🎁 <b>На какой подарок промокод?</b>\n\nВыбери конкретный или на все:",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardMarkup(keyboard=gift_rows, resize_keyboard=True)
    )

@dp.message(GiftStates.admin_promo_gift)
async def admin_promo_got_gift(message: Message, state: FSMContext):
    if message.from_user.id != OWNER_ID:
        return
    if message.text == "◀️ Назад":
        await state.set_state(GiftStates.admin_promo_discount)
        await message.answer("💰 На сколько звёзд скидка?")
        return

    if message.text == "🎁 На все подарки":
        await state.update_data(promo_gift_key=None, promo_gift_name="все подарки")
    else:
        found_key = None
        for key, gift in ALL_GIFTS.items():
            if message.text.startswith(f"{gift['emoji']} {gift['name']}"):
                found_key = key
                break
        if not found_key:
            await message.answer("❓ Выбери подарок из списка.")
            return
        await state.update_data(promo_gift_key=found_key, promo_gift_name=ALL_GIFTS[found_key]['name'])

    await state.set_state(GiftStates.admin_promo_activations)
    acts_kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="1"), KeyboardButton(text="5"), KeyboardButton(text="10")],
            [KeyboardButton(text="25"), KeyboardButton(text="50"), KeyboardButton(text="100")],
            [KeyboardButton(text="250"), KeyboardButton(text="500"), KeyboardButton(text="999")],
            [KeyboardButton(text="◀️ Назад")],
        ],
        resize_keyboard=True
    )
    await message.answer(
        "🔢 <b>Сколько активаций?</b>\n\nВыбери или введи число от 1 до 999:",
        parse_mode="HTML",
        reply_markup=acts_kb
    )

@dp.message(GiftStates.admin_promo_activations)
async def admin_promo_got_activations(message: Message, state: FSMContext):
    if message.from_user.id != OWNER_ID:
        return
    if message.text == "◀️ Назад":
        await state.set_state(GiftStates.admin_promo_gift)
        await message.answer("🎁 На какой подарок промокод?")
        return

    try:
        activations = int(message.text.strip())
        if activations < 1 or activations > 999:
            raise ValueError
    except ValueError:
        await message.answer("❗ Введи число от 1 до 999:")
        return

    await state.update_data(promo_activations=activations)
    await state.set_state(GiftStates.admin_promo_hours)

    hours_kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="1"), KeyboardButton(text="3"), KeyboardButton(text="6")],
            [KeyboardButton(text="12"), KeyboardButton(text="24"), KeyboardButton(text="48")],
            [KeyboardButton(text="72"), KeyboardButton(text="168"), KeyboardButton(text="720")],
            [KeyboardButton(text="◀️ Назад")],
        ],
        resize_keyboard=True
    )
    await message.answer(
        "⏳ <b>Через сколько часов промокод истечёт?</b>\n\n"
        "Выбери или введи число:\n"
        "<i>1ч · 3ч · 6ч · 12ч · 24ч · 48ч · 72ч · 168ч (7 дней) · 720ч (30 дней)</i>",
        parse_mode="HTML",
        reply_markup=hours_kb
    )

@dp.message(GiftStates.admin_promo_hours)
async def admin_promo_got_hours(message: Message, state: FSMContext):
    if message.from_user.id != OWNER_ID:
        return
    if message.text == "◀️ Назад":
        await state.set_state(GiftStates.admin_promo_activations)
        await message.answer("🔢 Сколько активаций?")
        return

    try:
        hours = int(message.text.strip())
        if hours < 1 or hours > 8760:
            raise ValueError
    except ValueError:
        await message.answer("❗ Введи число часов от 1 до 8760 (365 дней):")
        return

    await state.update_data(promo_hours=hours)
    await state.set_state(GiftStates.admin_promo_target)

    await message.answer(
        "👤 <b>Кому выдать промокод?</b>",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="👤 Себе"), KeyboardButton(text="👥 Покупателю")],
                [KeyboardButton(text="◀️ Назад")],
            ],
            resize_keyboard=True
        )
    )

@dp.message(GiftStates.admin_promo_target)
async def admin_promo_got_target(message: Message, state: FSMContext):
    if message.from_user.id != OWNER_ID:
        return
    if message.text == "◀️ Назад":
        await state.set_state(GiftStates.admin_promo_hours)
        await message.answer("⏳ Через сколько часов промокод истечёт?")
        return

    if message.text == "👤 Себе":
        await _finalize_promo(message, state, target_id=message.from_user.id, notify=False)
    elif message.text == "👥 Покупателю":
        await state.set_state(GiftStates.admin_promo_userid)
        await message.answer(
            "🆔 <b>Введите Telegram ID покупателя:</b>\n\n"
            "<i>Узнать ID можно через @userinfobot</i>",
            parse_mode="HTML",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="◀️ Назад")]],
                resize_keyboard=True
            )
        )
    else:
        await message.answer("❓ Нажми одну из кнопок.")

@dp.message(GiftStates.admin_promo_userid)
async def admin_promo_got_userid(message: Message, state: FSMContext):
    if message.from_user.id != OWNER_ID:
        return
    if message.text == "◀️ Назад":
        await state.set_state(GiftStates.admin_promo_target)
        await message.answer("👤 Кому выдать промокод?")
        return

    try:
        target_id = int(message.text.strip())
    except ValueError:
        await message.answer("❗ Введи числовой Telegram ID. Например: <code>123456789</code>", parse_mode="HTML")
        return

    await _finalize_promo(message, state, target_id=target_id, notify=True)

async def _finalize_promo(message: Message, state: FSMContext, target_id: int, notify: bool):
    data = await state.get_data()
    code = data["promo_code"]
    discount = data["promo_discount"]
    activations = data["promo_activations"]
    hours = data["promo_hours"]
    gift_key = data.get("promo_gift_key")
    gift_name = data.get("promo_gift_name", "все подарки")
    expires_at = datetime.now() + timedelta(hours=hours)

    await db_set_promo(code, {
        "discount_stars": discount,
        "activations_left": activations,
        "total_activations": activations,
        "gift_key": gift_key,
        "expires_at": expires_at,
        "used_by": set()
    })
    await db_set_user_promo(target_id, code, discount, gift_key)

    if hours < 24:
        expires_str = f"{hours} ч."
    elif hours < 168:
        expires_str = f"{hours // 24} дн."
    else:
        expires_str = f"{hours // 168} нед."

    if notify:
        gift_line = f"🎁 Подарок: <b>{gift_name}</b>\n" if gift_key else ""
        try:
            await bot.send_message(
                target_id,
                f"🎁 <b>Администратор подарил тебе промокод!</b>\n\n"
                f"🎟️ Код: <code>{code}</code>\n"
                f"💰 Скидка: <b>-{discount} ⭐</b>\n"
                f"{gift_line}"
                f"⏳ Действует: <b>{expires_str}</b>\n\n"
                f"Скидка уже активна — при покупке цена изменится автоматически! 🎉",
                parse_mode="HTML"
            )
            delivered = "✅ Сообщение покупателю отправлено."
        except TelegramForbiddenError:
            delivered = "⚠️ Покупатель заблокировал бота — сообщение не доставлено."
        except Exception:
            delivered = "⚠️ Не удалось отправить сообщение покупателю (он не запускал бота)."
    else:
        delivered = ""

    await state.clear()
    await message.answer(
        f"✅ <b>Промокод создан и активирован!</b>\n\n"
        f"🎟️ Код: <code>{code}</code>\n"
        f"💰 Скидка: <b>-{discount} ⭐</b>\n"
        f"🎁 На подарок: <b>{gift_name}</b>\n"
        f"🔢 Активаций: <b>{activations}</b>\n"
        f"⏳ Действует: <b>{expires_str}</b> (до {expires_at.strftime('%d.%m.%Y %H:%M')})\n"
        + (f"\n{delivered}" if delivered else ""),
        parse_mode="HTML",
        reply_markup=admin_main_kb()
    )

@dp.message(F.text == "🗑️ Удалить промокод")
async def admin_delete_promo(message: Message, state: FSMContext):
    if message.from_user.id != OWNER_ID:
        return
    all_promos = await db_get_all_promos()
    if not all_promos:
        await message.answer("Нет активных промокодов для удаления.", reply_markup=admin_main_kb())
        return

    kb_rows = [[KeyboardButton(text=code)] for code in all_promos]
    kb_rows.append([KeyboardButton(text="◀️ Назад")])
    await message.answer(
        "🗑️ <b>Выбери промокод для удаления:</b>",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardMarkup(keyboard=kb_rows, resize_keyboard=True, one_time_keyboard=True)
    )
    await state.set_state(GiftStates.admin_promo_name)
    await state.update_data(delete_mode=True)

# ==================== ОТПРАВКА ПОДАРКА ВЛАДЕЛЬЦЕМ ====================

async def owner_gifts_kb() -> ReplyKeyboardMarkup:
    rows = []
    for key, gift in ALL_GIFTS.items():
        price = await get_gift_price(key)
        rows.append([KeyboardButton(text=f"{gift['emoji']} {gift['name']} — {price} ⭐")])
    rows.append([KeyboardButton(text="◀️ Назад")])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True, one_time_keyboard=True)

@dp.message(F.text == "🎀 Отправить подарок")
async def owner_send_start(message: Message, state: FSMContext):
    if message.from_user.id != OWNER_ID:
        return
    await state.set_state(GiftStates.owner_send_userid)
    await message.answer(
        "🆔 <b>Введи Telegram ID получателя:</b>\n\n"
        "<i>Человек должен был запустить бота!</i>",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="◀️ Назад")]],
            resize_keyboard=True
        )
    )

@dp.message(GiftStates.owner_send_userid)
async def owner_got_userid(message: Message, state: FSMContext):
    if message.from_user.id != OWNER_ID:
        return
    if message.text == "◀️ Назад":
        await state.clear()
        await message.answer("⚙️ Админ панель", reply_markup=admin_main_kb())
        return
    try:
        target_id = int(message.text.strip())
    except ValueError:
        await message.answer(
            "❗ Введи числовой ID. Например: <code>123456789</code>",
            parse_mode="HTML"
        )
        return
    await state.update_data(owner_target_id=target_id)
    await state.set_state(GiftStates.owner_send_gift)
    await message.answer(
        f"✅ Получатель: <code>{target_id}</code>\n\n🎁 <b>Выбери подарок:</b>",
        parse_mode="HTML",
        reply_markup=await owner_gifts_kb()
    )

@dp.message(GiftStates.owner_send_gift)
async def owner_got_gift(message: Message, state: FSMContext):
    if message.from_user.id != OWNER_ID:
        return
    if message.text == "◀️ Назад":
        await state.set_state(GiftStates.owner_send_userid)
        await message.answer(
            "🆔 Введи Telegram ID получателя:",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="◀️ Назад")]],
                resize_keyboard=True
            )
        )
        return

    selected_key = None
    for key, gift in ALL_GIFTS.items():
        price = await get_gift_price(key)
        if message.text == f"{gift['emoji']} {gift['name']} — {price} ⭐":
            selected_key = key
            break

    if not selected_key:
        await message.answer("❓ Выбери подарок из списка.", reply_markup=await owner_gifts_kb())
        return

    await state.update_data(owner_gift_key=selected_key)
    await state.set_state(GiftStates.owner_send_comment)
    gift = ALL_GIFTS[selected_key]
    await message.answer(
        f"✅ Подарок: {gift['emoji']} <b>{gift['name']}</b>\n\n"
        f"💬 Напиши комментарий к подарку или нажми <b>«Без комментария»</b>:",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="🚫 Без комментария")],
                [KeyboardButton(text="◀️ Назад")],
            ],
            resize_keyboard=True
        )
    )

@dp.message(GiftStates.owner_send_comment)
async def owner_got_comment(message: Message, state: FSMContext):
    if message.from_user.id != OWNER_ID:
        return
    if message.text == "◀️ Назад":
        await state.set_state(GiftStates.owner_send_gift)
        data = await state.get_data()
        target_id = data.get("owner_target_id")
        await message.answer(
            f"🎁 <b>Выбери подарок</b> для <code>{target_id}</code>:",
            parse_mode="HTML",
            reply_markup=await owner_gifts_kb()
        )
        return

    comment = "" if message.text == "🚫 Без комментария" else message.text[:200]
    data = await state.get_data()
    target_id = data["owner_target_id"]
    selected_key = data["owner_gift_key"]
    gift = ALL_GIFTS[selected_key]

    await state.clear()
    await message.answer(
        f"⏳ Отправляю {gift['emoji']} <b>{gift['name']}</b> пользователю <code>{target_id}</code>...",
        parse_mode="HTML",
        reply_markup=admin_main_kb()
    )
    try:
        await tg_send_gift(user_id=target_id, gift_id=str(gift["id"]), text=comment or None)
        await db_add_history(OWNER_ID, {
            "gift_key": selected_key, "gift_name": gift["name"], "emoji": gift["emoji"],
            "target": "friend", "friend_id": target_id,
            "stars": gift["real_price"], "date": datetime.now().strftime("%d.%m.%Y %H:%M")
        })
        confirm = f"✅ Подарок {gift['emoji']} <b>{gift['name']}</b> успешно отправлен пользователю <code>{target_id}</code>!"
        if comment:
            confirm += f"\n💬 Комментарий: <i>{comment}</i>"
        await message.answer(confirm, parse_mode="HTML", reply_markup=admin_main_kb())
        try:
            notif = f"🎁 Тебе отправили подарок: {gift['emoji']} <b>{gift['name']}</b>!"
            if comment:
                notif += f"\n💬 <i>{comment}</i>"
            await bot.send_message(target_id, notif, parse_mode="HTML")
        except (TelegramForbiddenError, Exception):
            pass
    except Exception as e:
        await message.answer(
            f"❌ Ошибка при отправке подарка: <code>{e}</code>\n\n"
            f"<i>Возможные причины:\n"
            f"— Пользователь не запускал бота\n"
            f"— Закрыты подарки в настройках приватности\n"
            f"— Недостаточно звёзд на балансе бота</i>",
            parse_mode="HTML",
            reply_markup=admin_main_kb()
        )

# ==================== ПРОСТЫЕ ПОДАРКИ (АДМИН) ====================

def owner_simple_gifts_kb() -> ReplyKeyboardMarkup:
    rows = []
    for key, gift in SIMPLE_GIFTS.items():
        rows.append([KeyboardButton(text=f"{gift['emoji']} {gift['name']}")])
    rows.append([KeyboardButton(text="◀️ Назад")])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True, one_time_keyboard=True)

@dp.message(F.text == "💝 Простые подарки")
async def owner_simple_start(message: Message, state: FSMContext):
    if message.from_user.id != OWNER_ID:
        return
    await state.set_state(GiftStates.owner_simple_userid)
    await message.answer(
        "🆔 <b>Введи Telegram ID получателя:</b>\n\n"
        "<i>Человек должен был запустить бота!</i>",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="◀️ Назад")]],
            resize_keyboard=True
        )
    )

@dp.message(GiftStates.owner_simple_userid)
async def owner_simple_got_userid(message: Message, state: FSMContext):
    if message.from_user.id != OWNER_ID:
        return
    if message.text == "◀️ Назад":
        await state.clear()
        await message.answer("⚙️ Админ панель", reply_markup=admin_main_kb())
        return
    try:
        target_id = int(message.text.strip())
    except ValueError:
        await message.answer(
            "❗ Введи числовой ID. Например: <code>123456789</code>",
            parse_mode="HTML"
        )
        return
    await state.update_data(simple_target_id=target_id)
    await state.set_state(GiftStates.owner_simple_gift)
    await message.answer(
        f"✅ Получатель: <code>{target_id}</code>\n\n💝 <b>Выбери простой подарок:</b>",
        parse_mode="HTML",
        reply_markup=owner_simple_gifts_kb()
    )

@dp.message(GiftStates.owner_simple_gift)
async def owner_simple_got_gift(message: Message, state: FSMContext):
    if message.from_user.id != OWNER_ID:
        return
    if message.text == "◀️ Назад":
        await state.set_state(GiftStates.owner_simple_userid)
        await message.answer(
            "🆔 Введи Telegram ID получателя:",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="◀️ Назад")]],
                resize_keyboard=True
            )
        )
        return

    selected_key = None
    for key, gift in SIMPLE_GIFTS.items():
        if message.text == f"{gift['emoji']} {gift['name']}":
            selected_key = key
            break

    if not selected_key:
        await message.answer("❓ Выбери подарок из списка.", reply_markup=owner_simple_gifts_kb())
        return

    await state.update_data(simple_gift_key=selected_key)
    await state.set_state(GiftStates.owner_simple_comment)
    gift = SIMPLE_GIFTS[selected_key]
    await message.answer(
        f"✅ Подарок: {gift['emoji']} <b>{gift['name']}</b>\n\n"
        f"💬 Напиши комментарий или нажми <b>«Без комментария»</b>:",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="🚫 Без комментария")],
                [KeyboardButton(text="◀️ Назад")],
            ],
            resize_keyboard=True
        )
    )

@dp.message(GiftStates.owner_simple_comment)
async def owner_simple_got_comment(message: Message, state: FSMContext):
    if message.from_user.id != OWNER_ID:
        return
    if message.text == "◀️ Назад":
        await state.set_state(GiftStates.owner_simple_gift)
        data = await state.get_data()
        target_id = data.get("simple_target_id")
        await message.answer(
            f"💝 <b>Выбери простой подарок</b> для <code>{target_id}</code>:",
            parse_mode="HTML",
            reply_markup=owner_simple_gifts_kb()
        )
        return

    comment = "" if message.text == "🚫 Без комментария" else message.text[:200]
    data = await state.get_data()
    target_id = data["simple_target_id"]
    selected_key = data["simple_gift_key"]
    gift = SIMPLE_GIFTS[selected_key]

    await state.clear()
    await message.answer(
        f"⏳ Отправляю {gift['emoji']} <b>{gift['name']}</b> пользователю <code>{target_id}</code>...",
        parse_mode="HTML",
        reply_markup=admin_main_kb()
    )
    try:
        await tg_send_gift(user_id=target_id, gift_id=str(gift["id"]), text=comment or None)
        confirm = (
            f"✅ Подарок {gift['emoji']} <b>{gift['name']}</b> "
            f"успешно отправлен пользователю <code>{target_id}</code>!"
        )
        if comment:
            confirm += f"\n💬 Комментарий: <i>{comment}</i>"
        await message.answer(confirm, parse_mode="HTML", reply_markup=admin_main_kb())
        try:
            notif = f"🎁 Тебе отправили подарок: {gift['emoji']} <b>{gift['name']}</b>!"
            if comment:
                notif += f"\n💬 <i>{comment}</i>"
            await bot.send_message(target_id, notif, parse_mode="HTML")
        except TelegramForbiddenError:
            pass  # Пользователь заблокировал бота — ничего страшного
        except Exception:
            pass
    except Exception as e:
        await message.answer(
            f"❌ Ошибка при отправке подарка: <code>{e}</code>\n\n"
            f"<i>Возможные причины:\n"
            f"— Пользователь не запускал бота\n"
            f"— Закрыты подарки в настройках приватности\n"
            f"— Недостаточно звёзд на балансе бота</i>",
            parse_mode="HTML",
            reply_markup=admin_main_kb()
        )

# ==================== ДОБАВЛЕНИЕ НОВОГО ПОДАРКА (АДМИН) ====================

@dp.message(F.text == "➕ Добавить подарок")
async def admin_add_gift_start(message: Message, state: FSMContext):
    if message.from_user.id != OWNER_ID:
        return
    await state.set_state(GiftStates.admin_add_gift_id)
    await message.answer(
        "➕ <b>Добавление нового подарка</b>\n\n"
        "Шаг 1/5: Введи <b>Telegram Gift ID</b> подарка\n\n"
        "<i>Это числовой ID подарка в Telegram (например: 5969796561943660080)</i>",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="◀️ Назад")]],
            resize_keyboard=True
        )
    )

@dp.message(GiftStates.admin_add_gift_id)
async def admin_add_gift_got_id(message: Message, state: FSMContext):
    if message.from_user.id != OWNER_ID:
        return
    if message.text == "◀️ Назад":
        await state.clear()
        await message.answer("⚙️ Админ панель", reply_markup=admin_main_kb())
        return
    gift_id = message.text.strip()
    if not gift_id.isdigit():
        await message.answer("❗ ID должен содержать только цифры. Например: <code>5969796561943660080</code>", parse_mode="HTML")
        return
    await state.update_data(new_gift_id=gift_id)
    await state.set_state(GiftStates.admin_add_gift_name)
    await message.answer(
        "Шаг 2/5: Введи <b>название</b> подарка\n\n"
        "Например: <code>Мишка на Хэллоуин</code>",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="◀️ Назад")]],
            resize_keyboard=True
        )
    )

@dp.message(GiftStates.admin_add_gift_name)
async def admin_add_gift_got_name(message: Message, state: FSMContext):
    if message.from_user.id != OWNER_ID:
        return
    if message.text == "◀️ Назад":
        await state.set_state(GiftStates.admin_add_gift_id)
        await message.answer("Шаг 1/5: Введи Telegram Gift ID подарка:", reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="◀️ Назад")]], resize_keyboard=True))
        return
    name = message.text.strip()
    if len(name) < 2 or len(name) > 60:
        await message.answer("❗ Название: от 2 до 60 символов.")
        return
    await state.update_data(new_gift_name=name)
    await state.set_state(GiftStates.admin_add_gift_emoji)
    await message.answer(
        "Шаг 3/5: Введи <b>эмодзи</b> подарка\n\nНапример: 🎃",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="◀️ Назад")]],
            resize_keyboard=True
        )
    )

@dp.message(GiftStates.admin_add_gift_emoji)
async def admin_add_gift_got_emoji(message: Message, state: FSMContext):
    if message.from_user.id != OWNER_ID:
        return
    if message.text == "◀️ Назад":
        await state.set_state(GiftStates.admin_add_gift_name)
        await message.answer("Шаг 2/5: Введи название подарка:", reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="◀️ Назад")]], resize_keyboard=True))
        return
    emoji = message.text.strip()
    if len(emoji) > 10:
        await message.answer("❗ Слишком длинное эмодзи. Введи 1-2 символа.")
        return
    await state.update_data(new_gift_emoji=emoji)
    await state.set_state(GiftStates.admin_add_gift_price)
    await message.answer(
        "Шаг 4/5: Введи <b>цену в звёздах</b>\n\nНапример: <code>60</code>",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="◀️ Назад")]],
            resize_keyboard=True
        )
    )

@dp.message(GiftStates.admin_add_gift_price)
async def admin_add_gift_got_price(message: Message, state: FSMContext):
    if message.from_user.id != OWNER_ID:
        return
    if message.text == "◀️ Назад":
        await state.set_state(GiftStates.admin_add_gift_emoji)
        await message.answer("Шаг 3/5: Введи эмодзи подарка:", reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="◀️ Назад")]], resize_keyboard=True))
        return
    try:
        price = int(message.text.strip())
        if price < 1 or price > 10000:
            raise ValueError
    except ValueError:
        await message.answer("❗ Введи корректное число от 1 до 10000.")
        return
    await state.update_data(new_gift_price=price)
    await state.set_state(GiftStates.admin_add_gift_desc)
    await message.answer(
        "Шаг 5/5: Введи <b>описание</b> подарка\n\nНапример: <code>Хэллоуинский мишка 🎃</code>",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="◀️ Назад")]],
            resize_keyboard=True
        )
    )

@dp.message(GiftStates.admin_add_gift_desc)
async def admin_add_gift_got_desc(message: Message, state: FSMContext):
    if message.from_user.id != OWNER_ID:
        return
    if message.text == "◀️ Назад":
        await state.set_state(GiftStates.admin_add_gift_price)
        await message.answer("Шаг 4/5: Введи цену в звёздах:", reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="◀️ Назад")]], resize_keyboard=True))
        return
    desc = message.text.strip()
    if len(desc) < 2 or len(desc) > 200:
        await message.answer("❗ Описание: от 2 до 200 символов.")
        return
    await state.update_data(new_gift_desc=desc)
    data = await state.get_data()
    await state.set_state(GiftStates.admin_add_gift_confirm)
    await message.answer(
        f"✅ <b>Проверь данные нового подарка:</b>\n\n"
        f"🆔 ID: <code>{data['new_gift_id']}</code>\n"
        f"📛 Название: <b>{data['new_gift_name']}</b>\n"
        f"🎭 Эмодзи: {data['new_gift_emoji']}\n"
        f"💰 Цена: <b>{data['new_gift_price']} ⭐</b>\n"
        f"📝 Описание: <i>{desc}</i>\n\n"
        f"Сохранить подарок?",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="✅ Сохранить")],
                [KeyboardButton(text="◀️ Назад"), KeyboardButton(text="❌ Отмена")],
            ],
            resize_keyboard=True
        )
    )

@dp.message(GiftStates.admin_add_gift_confirm)
async def admin_add_gift_confirm(message: Message, state: FSMContext):
    if message.from_user.id != OWNER_ID:
        return
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("❌ Отменено.", reply_markup=admin_main_kb())
        return
    if message.text == "◀️ Назад":
        await state.set_state(GiftStates.admin_add_gift_desc)
        await message.answer("Шаг 5/5: Введи описание подарка:", reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="◀️ Назад")]], resize_keyboard=True))
        return
    if message.text != "✅ Сохранить":
        return

    data = await state.get_data()
    gift_key = f"custom_{data['new_gift_id']}"
    new_gift = {
        "id": data["new_gift_id"],
        "name": data["new_gift_name"],
        "emoji": data["new_gift_emoji"],
        "price_stars": data["new_gift_price"],
        "real_price": data["new_gift_price"],
        "description": data["new_gift_desc"],
        "sticker_id": None,
    }

    await db_add_custom_gift(gift_key, new_gift)
    GIFTS[gift_key] = new_gift
    ALL_GIFTS[gift_key] = new_gift

    await state.clear()
    await message.answer(
        f"🎉 <b>Подарок добавлен!</b>\n\n"
        f"{new_gift['emoji']} <b>{new_gift['name']}</b>\n"
        f"💰 Цена: {new_gift['price_stars']} ⭐\n\n"
        f"Теперь он доступен в каталоге подарков!",
        parse_mode="HTML",
        reply_markup=admin_main_kb()
    )

# ==================== УДАЛЕНИЕ КАСТОМНОГО ПОДАРКА (АДМИН) ====================

async def admin_custom_gifts_kb() -> ReplyKeyboardMarkup:
    custom = await db_get_all_custom_gifts()
    rows = []
    for key, gift in custom.items():
        rows.append([KeyboardButton(text=f"🗑 {gift['emoji']} {gift['name']}")])
    rows.append([KeyboardButton(text="◀️ Назад")])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True, one_time_keyboard=True)

@dp.message(F.text == "🗑️ Удалить подарок")
async def admin_del_gift_start(message: Message, state: FSMContext):
    if message.from_user.id != OWNER_ID:
        return
    custom = await db_get_all_custom_gifts()
    if not custom:
        await message.answer(
            "ℹ️ Нет добавленных кастомных подарков для удаления.",
            reply_markup=admin_main_kb()
        )
        return
    await state.set_state(GiftStates.admin_del_gift_select)
    await message.answer(
        "🗑️ <b>Выбери подарок для удаления:</b>\n\n"
        "<i>Удалить можно только подарки, добавленные через админку</i>",
        parse_mode="HTML",
        reply_markup=await admin_custom_gifts_kb()
    )

@dp.message(GiftStates.admin_del_gift_select)
async def admin_del_gift_selected(message: Message, state: FSMContext):
    if message.from_user.id != OWNER_ID:
        return
    if message.text == "◀️ Назад":
        await state.clear()
        await message.answer("⚙️ Админ панель", reply_markup=admin_main_kb())
        return

    custom = await db_get_all_custom_gifts()
    selected_key = None
    for key, gift in custom.items():
        if message.text == f"🗑 {gift['emoji']} {gift['name']}":
            selected_key = key
            break

    if not selected_key:
        await message.answer("❓ Выбери подарок из списка.", reply_markup=await admin_custom_gifts_kb())
        return

    gift = custom[selected_key]
    await db_delete_custom_gift(selected_key)
    # Удаляем из памяти
    GIFTS.pop(selected_key, None)
    ALL_GIFTS.pop(selected_key, None)

    await state.clear()
    await message.answer(
        f"🗑️ <b>Подарок удалён!</b>\n\n"
        f"{gift['emoji']} <b>{gift['name']}</b> больше не доступен в каталоге.",
        parse_mode="HTML",
        reply_markup=admin_main_kb()
    )

# ==================== /stopprom ====================

@dp.message(Command("stopprom"))
async def cmd_stopprom(message: Message):
    if message.from_user.id != OWNER_ID:
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(
            "❗ <b>Использование:</b> <code>/stopprom название</code>\n\n"
            "Например: <code>/stopprom -10starbotused</code>",
            parse_mode="HTML"
        )
        return

    code = args[1].strip()
    promo = await db_get_promo(code)
    if not promo:
        await message.answer(
            f"❓ Промокод <code>{code}</code> не найден.",
            parse_mode="HTML"
        )
        return

    await db_delete_promo(code)
    users_with_promo = await db_get_users_with_promo(code)
    await db_delete_promo_from_users(code)

    users_line = f"\n👥 Сброшен у {len(users_with_promo)} пользователей." if users_with_promo else ""
    await message.answer(
        f"🗑️ <b>Промокод <code>{code}</code> отключён!</b>{users_line}",
        parse_mode="HTML",
        reply_markup=admin_main_kb()
    )

# ==================== ЗАПУСК ====================

async def main():
    await init_db()
    # Загружаем кастомные подарки из БД в память
    await load_custom_gifts_to_memory()
    # Загружаем режим обслуживания из БД
    global maintenance_mode
    maintenance_mode = (await db_get_setting("maintenance_mode", "0")) == "1"
    print("🤖 Бот запущен! База данных: bot_data.db")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
