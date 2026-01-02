import os
import asyncio
import hashlib
import requests
import pdfplumber
from bs4 import BeautifulSoup
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor

TOKEN = os.getenv("TOKEN")
SITE_URL = "https://urgt66.ru/partition/136056/"
CHECK_INTERVAL = 1800  # 30 минут

bot = Bot(TOKEN)
dp = Dispatcher(bot)

os.makedirs("data", exist_ok=True)
PDF_PATH = "data/schedule.pdf"
HASH_PATH = "data/hash.txt"

USERS = set()


def get_latest_pdf_url():
    html = requests.get(SITE_URL).text
    soup = BeautifulSoup(html, "html.parser")
    for a in soup.find_all("a"):
        href = a.get("href", "")
        if href.endswith(".pdf"):
            return "https://urgt66.ru" + href
    return None


def get_hash(path):
    with open(path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()


async def check_updates():
    while True:
        try:
            pdf_url = get_latest_pdf_url()
            if not pdf_url:
                await asyncio.sleep(CHECK_INTERVAL)
                continue

            r = requests.get(pdf_url)
            with open(PDF_PATH, "wb") as f:
                f.write(r.content)

            new_hash = get_hash(PDF_PATH)
            old_hash = ""

            if os.path.exists(HASH_PATH):
                old_hash = open(HASH_PATH).read()

            if new_hash != old_hash:
                open(HASH_PATH, "w").write(new_hash)
                for user in USERS:
                    await bot.send_message(
                        user,
                        "📢 Расписание обновилось!\n"
                        "Используй: /schedule НАЗВАНИЕ_ГРУППЫ"
                    )

        except Exception as e:
            print("Ошибка:", e)

        await asyncio.sleep(CHECK_INTERVAL)


def get_group_schedule(group):
    text = ""
    with pdfplumber.open(PDF_PATH) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                text += t + "\n"

    lines = text.split("\n")
    result = []
    collecting = False

    for line in lines:
        if group in line:
            collecting = True
            result.append(line)
            continue
        if collecting:
            if line.strip() == "":
                break
            result.append(line)

    return "\n".join(result)


@dp.message_handler(commands=["start"])
async def start(msg: types.Message):
    USERS.add(msg.from_user.id)
    await msg.answer(
        "✅ Бот запущен\n\n"
        "📌 Команда:\n"
        "/schedule ИС-21"
    )


@dp.message_handler(commands=["schedule"])
async def schedule(msg: types.Message):
    group = msg.get_args()
    if not group:
        await msg.reply("❗️ Пример: /schedule ИС-21")
        return

    if not os.path.exists(PDF_PATH):
        await msg.reply("⏳ Расписание ещё не загружено")
        return

    result = get_group_schedule(group)
    if result:
        await msg.reply(f"📘 {group}:\n\n{result}")
    else:
        await msg.reply("❌ Группа не найдена")


if name == "__main__":
    dp.loop.create_task(check_updates())
    executor.start_polling(dp, skip_updates=True)
