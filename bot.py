
import logging
import time
import random
import string
import os
from datetime import datetime, timedelta
from pymongo import MongoClient
from flask import Flask, request
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, ContextTypes
import requests
import threading
import asyncio
from dotenv import load_dotenv

# === Load environment variables ===
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")
SHORTNER_API = os.getenv("SHORTNER_API")
FLASK_URL = os.getenv("FLASK_URL")
LIKE_API_URL = os.getenv("LIKE_API_URL")
PLAYER_INFO_API = os.getenv("PLAYER_INFO_API")
HOW_TO_VERIFY_URL = os.getenv("HOW_TO_VERIFY_URL")
VIP_ACCESS_URL = os.getenv("VIP_ACCESS_URL")

client = MongoClient(MONGO_URI)
db = client['likebot']
users = db['verifications']

flask_app = Flask(__name__)

@flask_app.route("/verify/<code>")
def verify(code):
    user = users.find_one({"code": code})
    if user and not user.get("verified"):
        users.update_one({"code": code}, {"$set": {"verified": True, "verified_at": datetime.utcnow()}})
        return "✅ Verification successful. Bot will now process your like."
    return "❌ Link expired or already used."

async def like_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    try:
        args = update.message.text.split()
        uid = args[2]
    except:
        await update.message.reply_text("❌ Format galat hai. Use: /like ind <uid>")
        return

    try:
        info = requests.get(PLAYER_INFO_API.format(uid=uid)).json()
        player_name = info.get("name", "Unknown")
    except:
        player_name = "Unknown"

    code = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
    short_link = requests.get(
        f"https://shortner.in/api?api={SHORTNER_API}&url={FLASK_URL}/verify/{code}"
    ).json()["shortenedUrl"]

    users.insert_one({
        "user_id": update.message.from_user.id,
        "uid": uid,
        "code": code,
        "verified": False,
        "expires_at": datetime.utcnow() + timedelta(minutes=10),
        "chat_id": update.effective_chat.id,
        "message_id": update.message.message_id
    })

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ VERIFY & SEND LIKE ✅", url=short_link)],
        [InlineKeyboardButton("❓ How to Verify ❓", url=HOW_TO_VERIFY_URL)],
        [InlineKeyboardButton("🧠 PURCHASE VIP & NO VERIFY", url=VIP_ACCESS_URL)]
    ])

    msg = f"🎯 *Like Request*\n\n👤 *From:* {player_name}\n🆔 *UID:* `{uid}`\n🌍 *Region:* IND\n⚠️ Verify within 10 minutes"
    await update.message.reply_text(msg, reply_markup=keyboard, parse_mode='Markdown')

async def process_verified_likes(app: Application):
    while True:
        pending = users.find({"verified": True, "processed": {"$ne": True}})
        for user in pending:
            uid = user['uid']
            api_resp = requests.get(LIKE_API_URL.format(uid=uid)).json()

            player = api_resp.get("name", "Unknown")
            before = api_resp.get("likes_before", 0)
            added = api_resp.get("likes_added", 0)
            total = before + added

            result = f"✅ *Request Processed Successfully*\n\n👤 *Player:* {player}\n🆔 *UID:* `{uid}`\n👍 *Likes Before:* {before}\n✨ *Likes Added:* {added}\n🇮🇳 *Total Likes Now:* {total}\n⏰ *Processed At:* {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}"

            try:
                await app.bot.send_message(
                    chat_id=user['chat_id'],
                    reply_to_message_id=user['message_id'],
                    text=result,
                    parse_mode='Markdown'
                )
            except Exception as e:
                print("Error sending message:", e)

            users.update_one({"_id": user['_id']}, {"$set": {"processed": True}})
        await asyncio.sleep(5)

def run_bot():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("like", like_command))

    thread = threading.Thread(target=flask_app.run, kwargs={"host": "0.0.0.0", "port": 5000})
    thread.start()

    asyncio.get_event_loop().create_task(process_verified_likes(app))
    app.run_polling()

if __name__ == '__main__':
    run_bot()
