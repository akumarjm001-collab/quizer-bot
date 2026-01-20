import csv
import asyncio
import os
import json
import io
from aiogram import Bot, Dispatcher, executor, types

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

questions = []
current_question = 0
scores = {}
poll_correct = {}
quiz_running = False

STATE_FILE = "state.json"

# ---------- STATE ----------

def save_state():
    with open(STATE_FILE, "w") as f:
        json.dump({
            "current_question": current_question,
            "scores": scores
        }, f)

def load_state():
    global current_question, scores
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            data = json.load(f)
            current_question = data.get("current_question", 0)
            scores = data.get("scores", {})

# ---------- COMMANDS ----------

@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    await message.reply("✅ Quizer Bot Ready\nCSV bhejo phir /startquiz")

@dp.message_handler(commands=["startquiz"])
async def start_quiz(message: types.Message):
    global current_question, scores, quiz_running

    if message.from_user.id != ADMIN_ID:
        return

    if not questions:
        await message.reply("❌ Pehle CSV upload karo")
        return

    quiz_running = False
    await asyncio.sleep(1)

    current_question = 0
    scores = {}
    quiz_running = True
    save_state()

    await message.reply("▶ Quiz Started")
    await quiz_loop(message.chat.id)

@dp.message_handler(commands=["resumequiz"])
async def resume_quiz(message: types.Message):
    global quiz_running

    if message.from_user.id != ADMIN_ID:
        return

    if not questions:
        await message.reply("❌ CSV missing, dobara upload karo")
        return

    load_state()
    quiz_running = True
    await message.reply("⏯ Quiz Resumed")
    await quiz_loop(message.chat.id)

# ---------- CSV UPLOAD (MEMORY) ----------

@dp.message_handler(content_types=types.ContentType.DOCUMENT)
async def upload_csv(message: types.Message):
    global questions

    if message.from_user.id != ADMIN_ID:
        return

    if not message.document.file_name.endswith(".csv"):
        await message.reply("❌ Sirf CSV file bhejo")
        return

    file = await bot.get_file(message.document.file_id)
    file_bytes = await bot.download_file(file.file_path)

    decoded = file_bytes.read().decode("utf-8")
    reader = csv.DictReader(io.StringIO(decoded))

    questions = list(reader)

    if os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)

    await message.reply(f"✅ CSV Loaded ({len(questions)} questions)")

# ---------- QUIZ LOOP ----------

async def quiz_loop(chat_id):
    global current_question, quiz_running

    while quiz_running and current_question < len(questions):
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

    if quiz_running:
        await show_result(chat_id)
        quiz_running = False
        if os.path.exists(STATE_FILE):
            os.remove(STATE_FILE)

# ---------- ANSWERS ----------

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
        await bot.send_message(chat_id, "❌ No participants")
        return

    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    text = "🏆 QUIZ RESULT 🏆\n\n"
    for i, (uid, score) in enumerate(sorted_scores[:10], start=1):
        user = await bot.get_chat(int(uid))
        text += f"{i}. {user.first_name} — {score}/{len(questions)}\n"

    await bot.send_message(chat_id, text)

# ---------- START ----------

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
