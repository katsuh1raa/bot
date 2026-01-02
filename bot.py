import os
import asyncio
import hashlib
import requests
from datetime import datetime
from bs4 import BeautifulSoup

from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ================== НАСТРОЙКИ ==================

TOKEN = "8391667886:AAGZOemUTi_8EUnqFh65WxKfjK1SyeizAdk"
ADMIN_ID = 7028713990

SITE_URL = "https://urgt66.ru/partition/136056/"
CHECK_INTERVAL = 1800  # 30 минут

DATA_DIR = "data"
PDF_PATH = f"{DATA_DIR}/schedule.pdf"
HASH_PATH = f"{DATA_DIR}/hash.txt"
USERS_PATH = f"{DATA_DIR}/users.txt"
HISTORY_DIR = f"{DATA_DIR}/history"

os.makedirs(HISTORY_DIR, exist_ok=True)

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# ================== ПОЛЬЗОВАТЕЛИ ==================

def load_users():
    if not os.path.exists(USERS_PATH):
        return set()
    with open(USERS_PATH, "r") as f:
        return set(map(int, f.read().splitlines()))

def save_users():
    with open(USERS_PATH, "w") as f:
        for u in USERS:
            f.write(f"{u}\n")

USERS = load_users()

# ================== PDF ==================

def get_latest_pdf_url():
    html = requests.get(SITE_URL, timeout=15).text
    soup = BeautifulSoup(html, "html.parser")

    pdfs = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.endswith(".pdf"):
            pdfs.append("https://urgt66.ru" + href)

    return pdfs[-1] if pdfs else None

def get_hash(path):
    with open(path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()

async def send_pdf_to_all(caption):
    for uid in USERS.copy():
        try:
            await bot.send_document(uid, open(PDF_PATH, "rb"), caption=caption)
        except:
            USERS.discard(uid)
    save_users()

async def check_once(startup=False):
    pdf_url = get_latest_pdf_url()
    if not pdf_url:
        return

    r = requests.get(pdf_url, timeout=20)
    with open(PDF_PATH, "wb") as f:
        f.write(r.content)

    new_hash = get_hash(PDF_PATH)
    old_hash = open(HASH_PATH).read() if os.path.exists(HASH_PATH) else ""

    if new_hash != old_hash or startup:
        with open(HASH_PATH, "w") as f:
            f.write(new_hash)

        ts = datetime.now().strftime("%Y-%m-%d_%H-%M")
        hist = f"{HISTORY_DIR}/schedule_{ts}.pdf"
        with open(hist, "wb") as f:
            f.write(r.content)

        await send_pdf_to_all("📘 Актуальное расписание")

# ================== ФОН ==================

async def checker():
    await check_once(startup=True)
    while True:
        await check_once()
        await asyncio.sleep(CHECK_INTERVAL)

# ================== АДМИН ==================

def admin_kb():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("📤 Разослать PDF", callback_data="send"),
        InlineKeyboardButton("🔄 Проверить сайт", callback_data="check"),
        InlineKeyboardButton("👥 Пользователи", callback_data="users"),
        InlineKeyboardButton("🗑 Удалить пользователя", callback_data="remove"),
        InlineKeyboardButton("📚 История PDF", callback_data="history"),
    )
    return kb

@dp.message_handler(commands=["admin"])
async def admin(msg: types.Message):
    if msg.from_user.id == ADMIN_ID:
        await msg.answer("🛠 Админ-панель", reply_markup=admin_kb())

@dp.callback_query_handler(lambda c: c.from_user.id == ADMIN_ID)
async def admin_buttons(c: types.CallbackQuery):
    if c.data == "send":
        await send_pdf_to_all("📘 Расписание (вручную)")
        await c.message.answer("✅ Отправлено")

    elif c.data == "check":
        await check_once()
        await c.message.answer("✅ Проверено")

    elif c.data == "users":
        await c.message.answer("👥 Пользователи:\n" + "\n".join(map(str, USERS)))

    elif c.data == "remove":
        await c.message.answer("✏️ Отправь ID пользователя")

    elif c.data == "history":
        files = sorted(os.listdir(HISTORY_DIR))[-5:]
        for f in files:
            await bot.send_document(ADMIN_ID, open(f"{HISTORY_DIR}/{f}", "rb"))

# ================== ПОЛЬЗОВАТЕЛИ ==================

@dp.message_handler(commands=["start"])
async def start(msg: types.Message):
    USERS.add(msg.from_user.id)
    save_users()
    await msg.answer("✅ Ты подписан на обновления расписания")

@dp.message_handler(lambda m: m.text.isdigit())
async def remove_user(msg: types.Message):
    if msg.from_user.id != ADMIN_ID:
        return
    uid = int(msg.text)
    if uid in USERS:
        USERS.remove(uid)
        save_users()
        await msg.answer("✅ Пользователь удалён")

# ================== ЗАПУСК ==================

if __name__ == "__main__":
    dp.loop.create_task(checker())
    executor.start_polling(dp, skip_updates=True)

