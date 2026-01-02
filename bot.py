import os
import asyncio
import hashlib
import aiohttp
import json

from aiogram import Bot, Dispatcher, executor, types

TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise RuntimeError("TOKEN not set")

PDF_URL = "https://example.com/schedule.pdf"  # ← ЗАМЕНИ
CHECK_INTERVAL = 60  # секунд

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

USERS_FILE = "users.json"
last_hash = None


def load_users():
    if not os.path.exists(USERS_FILE):
        return set()
    with open(USERS_FILE, "r") as f:
        return set(json.load(f))


def save_users(users: set):
    with open(USERS_FILE, "w") as f:
        json.dump(list(users), f)


users = load_users()


@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    users.add(message.chat.id)
    save_users(users)
    await message.answer("✅ Ты подписан на обновления расписания")


async def download_pdf():
    async with aiohttp.ClientSession() as session:
        async with session.get(PDF_URL) as resp:
            if resp.status != 200:
                return None
            return await resp.read()


def get_hash(data: bytes):
    return hashlib.md5(data).hexdigest()


async def check_schedule():
    global last_hash

    await asyncio.sleep(5)

    while True:
        try:
            pdf_data = await download_pdf()
            if not pdf_data:
                await asyncio.sleep(CHECK_INTERVAL)
                continue

            current_hash = get_hash(pdf_data)

            if current_hash != last_hash:
                last_hash = current_hash

                for uid in list(users):
                    try:
                        await bot.send_document(
                            uid,
                            ("schedule.pdf", pdf_data),
                            caption="📢 Обновлённое расписание"
                        )
                    except Exception as e:
                        print(f"Не удалось отправить {uid}: {e}")

        except Exception as e:
            print("Ошибка:", e)

        await asyncio.sleep(CHECK_INTERVAL)


async def on_startup(dp):
    asyncio.create_task(check_schedule())


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
