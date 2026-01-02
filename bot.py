import os
import asyncio
import hashlib
import requests
from bs4 import BeautifulSoup
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor

# ===== НАСТРОЙКИ =====
BOT_TOKEN = os.getenv("BOT_TOKEN")
SITE_URL = "https://urgt66.ru/partition/136056/"
CHECK_INTERVAL = 1800  # 30 минут

DATA_DIR = "data"
PDF_PATH = f"{DATA_DIR}/schedule.pdf"
HASH_PATH = f"{DATA_DIR}/hash.txt"

os.makedirs(DATA_DIR, exist_ok=True)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

USERS = set()


# ===== ВСПОМОГАТЕЛЬНОЕ =====
def get_latest_pdf_url():
    html = requests.get(SITE_URL, timeout=15).text
    soup = BeautifulSoup(html, "html.parser")
    for a in soup.find_all("a"):
        href = a.get("href", "")
        if href.endswith(".pdf"):
            return "https://urgt66.ru" + href
    return None


def file_hash(path):
    with open(path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()


def download_pdf(url):
    r = requests.get(url, timeout=30)
    with open(PDF_PATH, "wb") as f:
        f.write(r.content)


# ===== ПРОВЕРКА ОБНОВЛЕНИЙ =====
async def check_updates():
    await asyncio.sleep(10)  # даём боту стартануть
    while True:
        try:
            pdf_url = get_latest_pdf_url()
            if not pdf_url:
                await asyncio.sleep(CHECK_INTERVAL)
                continue

            download_pdf(pdf_url)
            new_hash = file_hash(PDF_PATH)

            old_hash = ""
            if os.path.exists(HASH_PATH):
                with open(HASH_PATH) as f:
                    old_hash = f.read()

            if new_hash != old_hash:
                with open(HASH_PATH, "w") as f:
                    f.write(new_hash)

                for user in USERS:
                    await bot.send_document(
                        user,
                        open(PDF_PATH, "rb"),
                        caption="📢 Обновлённое расписание"
                    )

        except Exception as e:
            print("Ошибка проверки:", e)

        await asyncio.sleep(CHECK_INTERVAL)


# ===== КОМАНДЫ =====
@dp.message_handler(commands=["start"])
async def start(msg: types.Message):
    USERS.add(msg.from_user.id)
    await msg.answer(
        "✅ Ты подписан на обновления расписаний\n\n"
        "📄 /last — последнее расписание"
    )


@dp.message_handler(commands=["last"])
async def last(msg: types.Message):
    if not os.path.exists(PDF_PATH):
        await msg.answer("⏳ Расписание ещё не загружено")
        return

    await msg.answer_document(
        open(PDF_PATH, "rb"),
        caption="📄 Последнее расписание"
    )


# ===== ЗАПУСК =====
if __name__ == "__main__":
    dp.loop.create_task(check_updates())
    executor.start_polling(dp, skip_updates=True)
