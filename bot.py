import csv
import asyncio
import os
import json
from aiogram import Bot, Dispatcher, executor, types

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

DATA_FILE = "state.json"
CSV_FILE = "quiz.csv"

questions = []
current_question = 0
scores = {}
poll_correct = {}

# ---------- STATE SAVE / LOAD ----------

def save_state():
    data = {
        "current_question": current_question,
        "scores": scores
    }
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

def load_state():
    global current_question, scores
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
            current_question = data.get("current_question", 0)
            scores = data.get("scores", {})

# ---------- CSV LOAD ----------

def load_csv():
    questions.clear()
    with open(CSV_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            questions.append(row)

# ---------- COMMANDS ----------

@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    await message.reply("✅ Quizer Bot Ready")

@dp.message_handler(commands=["startquiz"])
async def start_quiz(message: types.Message):
    global current_question, scores

    if message.from_user.id != ADMIN_ID:
        return

    if not os.path.exists(CSV_FILE):
        await message.reply("❌ CSV file upload nahi hai")
        return

    current_question = 0
    scores = {}
    load_csv()
    save_state()

    await message.reply("▶ Quiz Started")
    await send_question(message.chat.id)

@dp.message_handler(commands=["resumequiz"])
async def resume_quiz(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return

    if not os.path.exists(DATA_FILE):
        await message.reply("❌ Resume data nahi mila")
        return

    load_state()
    load_csv()
    await message.reply("⏯ Quiz Resumed")
    await send_question(message.chat.id)

# ---------- CSV UPLOAD ----------

@dp.message_handler(content_types=types.ContentType.DOCUMENT)
async def upload_csv(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return

    if not message.document.file_name.endswith(".csv"):
        await message.reply("❌ Sirf CSV file bhejo")
        return

    file = await bot.get_file(message.document.file_id)
    await bot.download_file(file.file_path, CSV_FILE)

    await message.reply("✅ CSV Uploaded Successfully")

# ---------- QUIZ FLOW ----------

async def send_question(chat_id):
    global current_question

    if current_question >= len(questions):
        await show_result(chat_id)
        return

    q = questions[current_question]
    options = [q["option_a"], q["option_b"], q["option_c"], q["option_d"]]
    correct = ord(q["answer"].upper()) - 65

    poll = await bot.send_poll(
        chat_id,
        q["question"],
        options,
        type="quiz",
        correct_option_id=correct,
        is_anonymous=False,
        open_period=15
    )

    poll_correct[poll.poll.id] = correct
    current_question += 1
    save_state()

    await asyncio.sleep(16)
    await send_question(chat_id)

@dp.poll_answer_handler()
async def handle_answer(poll_answer: types.PollAnswer):
    uid = str(poll_answer.user.id)
    chosen = poll_answer.option_ids[0]
    poll_id = poll_answer.poll_id

    if uid not in scores:
        scores[uid] = 0

    if poll_id in poll_correct and chosen == poll_correct[poll_id]:
        scores[uid] += 1

    save_state()

# ---------- RESULT ----------

async def show_result(chat_id):
    if not scores:
        await bot.send_message(chat_id, "No participants")
        return

    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    text = "🏆 QUIZ RESULT 🏆\n\n"
    rank = 1
    for uid, score in sorted_scores[:10]:
        user = await bot.get_chat(int(uid))
        text += f"{rank}. {user.first_name} — {score}/{len(questions)}\n"
        rank += 1

    await bot.send_message(chat_id, text)

    if os.path.exists(DATA_FILE):
        os.remove(DATA_FILE)

# ---------- START ----------

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
