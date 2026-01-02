import os
import asyncio
import hashlib
import aiohttp

from aiogram import Bot, Dispatcher, executor

TOKEN = os.getenv("TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID"))

SCHEDULE_URL = "https://example.com/schedule.pdf"  # ← ЗАМЕНИ
CHECK_INTERVAL = 30  # секунд

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

last_file_hash = None


async def download_file():
    async with aiohttp.ClientSession() as session:
        async with session.get(SCHEDULE_URL) as resp:
            if resp.status != 200:
                return None
            return await resp.read()


def get_hash(data: bytes):
    return hashlib.sha256(data).hexdigest()


async def watch_schedule():
    global last_file_hash

    await asyncio.sleep(5)

    while True:
        try:
            data = await download_file()
            if not data:
                await asyncio.sleep(CHECK_INTERVAL)
                continue

            file_hash = get_hash(data)

            if file_hash != last_file_hash:
                last_file_hash = file_hash

                filename = "schedule"
                await bot.send_document(
                    CHAT_ID,
                    ("schedule.pdf", data),
                    caption="🔄 Обновлённое расписание"
                )

        except Exception as e:
            print("Ошибка:", e)

        await asyncio.sleep(CHECK_INTERVAL)


async def on_startup(dp):
    asyncio.create_task(watch_schedule())


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
