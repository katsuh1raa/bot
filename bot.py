import os
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor

TOKEN = os.getenv("TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

DAYS = {
    "понедельник": 0,
    "вторник": 1,
    "среда": 2,
    "четверг": 3,
    "пятница": 4,
    "суббота": 5,
    "воскресенье": 6,
}


def load_schedule():
    schedule = {i: [] for i in range(7)}
    current_day = None

    with open("schedule.txt", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if not line:
                continue

            if line.startswith("#"):
                day_name = line[1:].strip().lower()
                current_day = DAYS.get(day_name)
                continue

            if current_day is not None and "|" in line:
                time, subject = line.split("|", 1)
                schedule[current_day].append((time.strip(), subject.strip()))

    return schedule


SCHEDULE = load_schedule()


def get_today_schedule():
    today = datetime.now().weekday()
    lessons = SCHEDULE.get(today, [])

    if not lessons:
        return "📭 *Сегодня занятий нет*"

    text = "📅 *Актуальное расписание на сегодня:*\n\n"
    for time, subject in lessons:
        text += f"🕒 {time} — {subject}\n"

    return text


@dp.message_handler(commands=["start"])
async def start_handler(message: types.Message):
    await message.answer(
        "👋 Привет!\n\n" + get_today_schedule(),
        parse_mode="Markdown"
    )


if __name__ == "__main__":
    print("Bot started")
    executor.start_polling(dp, skip_updates=True)
