import csv
import asyncio
import os
from aiogram import Bot, Dispatcher, executor, types

# 🔐 ENV VARIABLES (Render se aayenge)
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

questions = []

def load_csv():
    questions.clear()
    with open("quiz.csv", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            questions.append(row)

@dp.message_handler(commands=["start"])
async def start_cmd(message: types.Message):
    await message.reply("✅ Quizer Bot is LIVE\nUse /startquiz")

@dp.message_handler(commands=["startquiz"])
async def start_quiz(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return await message.reply("❌ You are not admin")

    load_csv()

    for q in questions:
        options = [
            q["option_a"],
            q["option_b"],
            q["option_c"],
            q["option_d"]
        ]

        correct = ord(q["answer"].strip().upper()) - 65

        await bot.send_poll(
            chat_id=message.chat.id,
            question=q["question"],
            options=options,
            type="quiz",
            correct_option_id=correct,
            is_anonymous=False,
            open_period=15
        )

        await asyncio.sleep(16)

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
