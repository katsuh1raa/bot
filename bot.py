import asyncio
import hashlib
import os
import aiohttp
from aiogram import Bot, Dispatcher, executor, types

TOKEN = os.getenv("BOT_TOKEN")
PDF_URL = "https://example.com/schedule.pdf"  # <-- ТВОЙ PDF
CHECK_INTERVAL = 300

ADMINS = [7028713990]  # <-- ТВОЙ TELEGRAM ID

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

USERS_FILE = "users.txt"
BANNED_FILE = "banned.txt"
HASH_FILE = "last_hash.txt"
PDF_FILE = "schedule.pdf"


# --------- Utils ----------
def read_ids(file):
    if not os.path.exists(file):
        return []
    with open(file) as f:
        return [int(x) for x in f.read().splitlines() if x.strip()]


def write_id(file, uid):
    ids = read_ids(file)
    if uid not in ids:
        with open(file, "a") as f:
            f.write(f"{uid}\n")


def is_admin(uid):
    return uid in ADMINS


# --------- PDF ----------
async def download_pdf():
    async with aiohttp.ClientSession() as session:
        async with session.get(PDF_URL) as r:
            if r.status != 200:
                return None
            data = await r.read()
            with open(PDF_FILE, "wb") as f:
                f.write(data)
            return data


def md5(data):
    return hashlib.md5(data).hexdigest()


def load_hash():
    return open(HASH_FILE).read().strip() if os.path.exists(HASH_FILE) else None


def save_hash(h):
    with open(HASH_FILE, "w") as f:
        f.write(h)


# --------- Broadcast ----------
async def send_pdf(users):
    for uid in users:
        try:
            await bot.send_document(uid, types.InputFile(PDF_FILE))
        except:
            pass


# --------- Checker ----------
async def checker():
    await asyncio.sleep(10)
    while True:
        try:
            data = await download_pdf()
            if data:
                new = md5(data)
                old = load_hash()
                if new != old:
                    save_hash(new)
                    await send_pdf(read_ids(USERS_FILE))
        except:
            pass
        await asyncio.sleep(CHECK_INTERVAL)


# --------- User ----------
@dp.message_handler(commands=["start"])
async def start(msg: types.Message):
    if msg.from_user.id in read_ids(BANNED_FILE):
        return
    write_id(USERS_FILE, msg.from_user.id)
    await msg.answer(
        "✅ Ты подписан на обновления расписания\n"
        "📄 /last — последнее расписание"
    )


@dp.message_handler(commands=["last"])
async def last(msg: types.Message):
    if os.path.exists(PDF_FILE):
        await msg.answer_document(types.InputFile(PDF_FILE))
    else:
        await msg.answer("Расписание ещё не загружено")


# ================= АДМИНКА =================

@dp.message_handler(commands=["admin"])
async def admin(msg: types.Message):
    if not is_admin(msg.from_user.id):
        return
    await msg.answer(
        "🛠 Админ-панель\n\n"
        "/users — пользователи\n"
        "/send — разослать PDF\n"
        "/update — обновить и разослать\n"
        "/ban ID\n"
        "/unban ID"
    )


@dp.message_handler(commands=["users"])
async def users(msg: types.Message):
    if not is_admin(msg.from_user.id):
        return
    users = read_ids(USERS_FILE)
    await msg.answer(f"👥 Пользователей: {len(users)}")


@dp.message_handler(commands=["send"])
async def send(msg: types.Message):
    if not is_admin(msg.from_user.id):
        return
    await send_pdf(read_ids(USERS_FILE))
    await msg.answer("✅ Рассылка выполнена")


@dp.message_handler(commands=["update"])
async def update(msg: types.Message):
    if not is_admin(msg.from_user.id):
        return
    data = await download_pdf()
    if data:
        save_hash(md5(data))
        await send_pdf(read_ids(USERS_FILE))
        await msg.answer("🔄 Обновлено и разослано")


@dp.message_handler(commands=["ban"])
async def ban(msg: types.Message):
    if not is_admin(msg.from_user.id):
        return
    try:
        uid = int(msg.text.split()[1])
        write_id(BANNED_FILE, uid)
        await msg.answer(f"🚫 Забанен {uid}")
    except:
        await msg.answer("❌ Используй: /ban ID")


@dp.message_handler(commands=["unban"])
async def unban(msg: types.Message):
    if not is_admin(msg.from_user.id):
        return
    try:
        uid = int(msg.text.split()[1])
        ids = read_ids(BANNED_FILE)
        ids.remove(uid)
        with open(BANNED_FILE, "w") as f:
            for i in ids:
                f.write(f"{i}\n")
        await msg.answer(f"✅ Разбанен {uid}")
    except:
        await msg.answer("❌ Ошибка")


# --------- Start ----------
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(checker())
    executor.start_polling(dp, skip_updates=True)


