import asyncio
import os
import hashlib
import requests
from bs4 import BeautifulSoup
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ================= НАСТРОЙКИ =================
TOKEN = "8391667886:AAGZOemUTi_8EUnqFh65WxKfjK1SyeizAdk"
ADMIN_ID = 7028713990

CHECK_INTERVAL = 300  # 5 минут
BASE_URL = "https://urgt66.ru"
PAGE_URL = "https://urgt66.ru/partition/136056/"

PDF_DIR = "pdf"
os.makedirs(PDF_DIR, exist_ok=True)

# =============================================

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

subscribers = set()
pdf_history = []
last_hash = None


def get_latest_pdf():
    r = requests.get(PAGE_URL, timeout=15)
    soup = BeautifulSoup(r.text, "html.parser")

    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.lower().endswith(".pdf"):
            links.append(BASE_URL + href)

    if not links:
        return None

    return links[0]  # на сайте последний — первый


def download_pdf(url):
    filename = url.split("/")[-1]
    path = os.path.join(PDF_DIR, filename)

    r = requests.get(url, timeout=20)
    with open(path, "wb") as f:
        f.write(r.content)

    h = hashlib.md5(r.content).hexdigest()
    return path, h


async def send_pdf_to_all(path):
    for uid in subscribers:
        try:
            await bot.send_document(uid, open(path, "rb"))
        except:
            pass


async def checker():
    global last_hash

    while True:
        try:
            url = get_latest_pdf()
            if not url:
                await asyncio.sleep(CHECK_INTERVAL)
                continue

            path, h = download_pdf(url)

            if h != last_hash:
                last_hash = h
                pdf_history.append(path)
                await send_pdf_to_all(path)

        except Exception as e:
            print("ERROR:", e)

        await asyncio.sleep(CHECK_INTERVAL)


# ================= КОМАНДЫ =================

@dp.message_handler(commands=["start"])
async def start(msg: types.Message):
    subscribers.add(msg.chat.id)

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("📄 Последнее расписание", callback_data="last"))

    if msg.chat.id == ADMIN_ID:
        kb.add(InlineKeyboardButton("🛠 Админ-панель", callback_data="admin"))

    await msg.answer(
        "✅ Ты подписан на обновления расписаний.\n"
        "Новое PDF придёт автоматически.",
        reply_markup=kb
    )

    if pdf_history:
        await bot.send_document(msg.chat.id, open(pdf_history[-1], "rb"))


@dp.callback_query_handler(lambda c: c.data == "last")
async def last_pdf(cb: types.CallbackQuery):
    if not pdf_history:
        await cb.answer("Нет данных", show_alert=True)
        return
    await bot.send_document(cb.message.chat.id, open(pdf_history[-1], "rb"))


@dp.callback_query_handler(lambda c: c.data == "admin")
async def admin_panel(cb: types.CallbackQuery):
    if cb.from_user.id != ADMIN_ID:
        return

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("👥 Пользователи", callback_data="users"))
    kb.add(InlineKeyboardButton("📂 История PDF", callback_data="history"))

    await cb.message.answer("🛠 Админ-панель", reply_markup=kb)


@dp.callback_query_handler(lambda c: c.data == "users")
async def users(cb: types.CallbackQuery):
    if cb.from_user.id != ADMIN_ID:
        return
    await cb.message.answer(f"👥 Подписчиков: {len(subscribers)}")


@dp.callback_query_handler(lambda c: c.data == "history")
async def history(cb: types.CallbackQuery):
    if cb.from_user.id != ADMIN_ID:
        return

    if not pdf_history:
        await cb.message.answer("История пуста")
        return

    for path in pdf_history[-5:]:
        await bot.send_document(ADMIN_ID, open(path, "rb"))


# ================= ЗАПУСК =================

async def on_startup(dp):
    asyncio.create_task(checker())
    print("Bot started")


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
