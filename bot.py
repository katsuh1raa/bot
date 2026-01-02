import asyncio
import hashlib
import os
import aiohttp
from aiogram import Bot, Dispatcher, executor, types

# ================= НАСТРОЙКИ =================
TOKEN = os.getenv("BOT_TOKEN")  # ОБЯЗАТЕЛЬНО в Railway
PDF_URL = "https://example.com/schedule.pdf"  # <-- СЮДА ССЫЛКУ НА PDF
CHECK_INTERVAL = 300  # проверка каждые 5 минут
# ============================================

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

USERS_FILE = "users.txt"
HASH_FILE = "last_hash.txt"
PDF_FILE = "schedule.pdf"


# ---------- Пользователи ----------
def get_users():
    if not os.path.exists(USERS_FILE):
        return []
    with open(USERS_FILE) as f:
        return [int(x) for x in f.read().splitlines() if x.strip()]


def add_user(user_id: int):
    users = get_users()
    if user_id not in users:
        with open(USERS_FILE, "a") as f:
            f.write(f"{user_id}\n")


# ---------- PDF ----------
async def download_pdf():
    async with aiohttp.ClientSession() as session:
        async with session.get(PDF_URL) as resp:
            if resp.status != 200:
                return None
            data = await resp.read()
            with open(PDF_FILE, "wb") as f:
                f.write(data)
            return data


def get_hash(data: bytes):
    return hashlib.md5(data).hexdigest()


def load_last_hash():
    if not os.path.exists(HASH_FILE):
        return None
    with open(HASH_FILE) as f:
        return f.read().strip()


def save_hash(h: str):
    with open(HASH_FILE, "w") as f:
        f.write(h)


# ---------- Рассылка ----------
async def send_pdf_to_all():
    users = get_users()
    for uid in users:
        try:
            await bot.send_document(uid, types.InputFile(PDF_FILE))
        except:
            pass


# ---------- Проверка обновлений ----------
async def checker():
    await asyncio.sleep(10)
    while True:
        try:
            data = await download_pdf()
            if data:
                new_hash = get_hash(data)
                old_hash = load_last_hash()

                if new_h_
