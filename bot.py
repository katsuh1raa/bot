import os
import hashlib
import requests
import pdfplumber
from datetime import datetime
from bs4 import BeautifulSoup
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor

TOKEN = os.environ.get("TOKEN")
if not TOKEN:
    raise RuntimeError("TOKEN not set")

SITE_URL = "https://urgt66.ru/partition/136056/"
DATA_DIR = "data"
PDF_PATH = f"{DATA_DIR}/schedule.pdf"
HASH_PATH = f"{DATA_DIR}/hash.txt"

os.makedirs(DATA_DIR, exist_ok=True)

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)


def get_latest_pdf_url():
    r = requests.get(SITE_URL, timeout=15)
    soup = BeautifulSoup(r.text, "html.parser")
    for a in soup.find_all("a"):
        href = a.get("href", "")
        if href.endswith(".pdf"):
            return "https://urgt66.ru" + href
    return None


def file_hash(path):
    with open(path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()


def update_pdf():
    url = get_latest_pdf_url()
    if not url:
        return False

    r = requests.get(url, timeout=20)
    with open(PDF_PATH, "wb") as f:
        f.write(r.content)

    new_hash = file_hash(PDF_PATH)
    old_hash = open(HASH_PATH).read() if os.path.exists(HASH_PATH) else ""

    if new_hash != old_hash:
        with open(HASH_PATH, "w") as f:
            f.write(new_hash)
        return True

    return False


def today_schedule(group="ИС-21"):
    if not os.path.exists(PDF_PATH):
        return "⏳ Расписание ещё не загружено"

    text = ""
    with pdfplumber.open(PDF_PATH) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                text += t + "\n"

    lines = text.split("\n")
    result = []
    collect = False

    for line in lines:
        if group in line:
            collect = True
            result.append(line)
            continue
        if collect and not line.strip():
            break
        if collect:
            result.append(line)

    if not result:
        return "❌ Группа не найдена"

    return f"📘 Расписание {group}:\n\n" + "\n".join(result)


@dp.message_handler(commands=["start"])
async def start(msg: types.Message):
    update_pdf()
    await msg.answer(today_schedule())


@dp.message_handler(commands=["schedule"])
async def schedule(msg: types.Message):
    group = msg.get_args() or "ИС-21"
    update_pdf()
    await msg.answer(today_schedule(group))


if __name__ == "__main__":
    print("BOT STARTED")
    executor.start_polling(dp, skip_updates=True)
