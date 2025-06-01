
import os
import requests
import random
import string
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from dotenv import load_dotenv

load_dotenv()

CHANNEL_USERNAME = os.getenv("REQUIRED_CHANNEL")  # e.g., @mychannel
SHORTNER_API = os.getenv("SHORTNER_API")
FLASK_URL = os.getenv("FLASK_URL")
PLAYER_INFO_API = os.getenv("PLAYER_INFO_API")
HOW_TO_VERIFY_URL = os.getenv("HOW_TO_VERIFY_URL")
VIP_ACCESS_URL = os.getenv("VIP_ACCESS_URL")
db = None  # Mongo setup is expected in the main script

async def is_user_joined(bot, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception:
        return False

async def like_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    user_id = update.message.from_user.id
    if not await is_user_joined(context.bot, user_id):
        join_btn = InlineKeyboardMarkup([[
            InlineKeyboardButton("📢 JOIN CHANNEL", url=f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}")
        ]])
        await update.message.reply_text("📛 Please join our channel first to use this command.", reply_markup=join_btn)
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

    db['verifications'].insert_one({
        "user_id": user_id,
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
