
import logging
import time
import random
import string
import os
from datetime import datetime, timedelta
from pymongo import MongoClient
from flask import Flask, request
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
import requests
import threading
import asyncio
from dotenv import load_dotenv

# === Load .env variables ===
load_dotenv()

BOT_TOKEN = os.getenv("8069913528:AAEWO2u3DynQodZqqBYmt_fkhcc_VUwqhEQ")
MONGO_URI = os.getenv("mongodb+srv://dggaming:dggaming@cluster0.qnfxnzm.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
SHORTNER_API = os.getenv("0b3be11de98ce79a01b780153eaca00c1927c157")
FLASK_URL = os.getenv("https://ff-like-bot-3n6j.onrender.com")
LIKE_API_URL = os.getenv("https://dev-like-api-fgya.vercel.app/like?uid={uid}")

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

    code = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
    short_link = requests.get(f"https://shortner.in/api?api={SHORTNER_API}&url={FLASK_URL}/verify/{code}").json()["shortenedUrl"]

    users.insert_one({
        "user_id": update.message.from_user.id,
        "uid": uid,
        "code": code,
        "verified": False,
        "expires_at": datetime.utcnow() + timedelta(minutes=10),
        "chat_id": update.effective_chat.id,
        "message_id": update.message.message_id
    })

    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("✅ VERIFY & SEND LIKE", url=short_link)]])
    msg = f"🎯 *Like Request*\n\n🧑‍🚀 *From:* Ff\n🆔 *UID:* `{uid}`\n🌎 *Region:* IND\n⚠️ Verify within 10 minutes"
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
                await app.bot.send_message(chat_id=user['chat_id'], reply_to_message_id=user['message_id'], text=result, parse_mode='Markdown')
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
