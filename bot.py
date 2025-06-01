import logging import time import random import string import os from datetime import datetime, timedelta from pymongo import MongoClient from flask import Flask, request from telegram import Update, InlineKeyboardMarkup, InlineKeyimport logging
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

=== Load environment variables ===

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN") MONGO_URI = os.getenv("MONGO_URI") SHORTNER_API = os.getenv("SHORTNER_API") FLASK_URL = os.getenv("FLASK_URL") LIKE_API_URL = os.getenv("LIKE_API_URL") PLAYER_INFO_API = os.getenv("PLAYER_INFO_API") HOW_TO_VERIFY_URL = os.getenv("HOW_TO_VERIFY_URL") VIP_ACCESS_URL = os.getenv("VIP_ACCESS_URL") ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.isdigit()]

client = MongoClient(MONGO_URI) db = client['likebot'] users = db['verifications'] profiles = db['users']

flask_app = Flask(name)

@flask_app.route("/verify/<code>") def verify(code): user = users.find_one({"code": code}) if user and not user.get("verified"): users.update_one({"code": code}, {"$set": {"verified": True, "verified_at": datetime.utcnow()}}) return "✅ Verification successful. Bot will now process your like." return "❌ Link expired or already used."

async def like_command(update: Update, context: ContextTypes.DEFAULT_TYPE): if not update.message or not update.message.text: return

try:
    args = update.message.text.split()
    uid = args[2]
except:
    await update.message.reply_text("❌ Format galat hai. Use: /like ind <uid>")
    return

try:
    info = requests.get(PLAYER_INFO_API.format(uid=uid), timeout=5).json()
    player_name = info.get("name", f"Player-{uid[-4:]}")
    level = info.get("level", "?")
    rank = info.get("rank", "?")
except:
    player_name = f"Player-{uid[-4:]}"
    level = "?"
    rank = "?"

code = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
short_link = requests.get(
    f"https://shortner.in/api?api={SHORTNER_API}&url={FLASK_URL}/verify/{code}"
).json().get("shortenedUrl", f"{FLASK_URL}/verify/{code}")

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
    [InlineKeyboardButton("😇 PURCHASE VIP & NO VERIFY", url=VIP_ACCESS_URL)]
])

msg = f"🎯 *Like Request*\n\n👤 *From:* {player_name}\n🆔 *UID:* `{uid}`\n🏅 *Level:* {level}\n🎖 *Rank:* {rank}\n🌍 *Region:* IND\n⚠️ Verify within 10 minutes"
await update.message.reply_text(msg, reply_markup=keyboard, parse_mode='Markdown')

async def givevip_command(update: Update, context: ContextTypes.DEFAULT_TYPE): if update.effective_user.id not in ADMIN_IDS: await update.message.reply_text("🚫 You are not authorized to use this command.") return

try:
    target_id = int(context.args[0])
except:
    await update.message.reply_text("❌ Use: /givevip <user_id>")
    return

profiles.update_one({"user_id": target_id}, {"$set": {"is_vip": True}}, upsert=True)
await update.message.reply_text(f"✅ VIP access granted to user `{target_id}`", parse_mode='Markdown')

async def process_verified_likes(app: Application): while True: pending = users.find({"verified": True, "processed": {"$ne": True}}) for user in pending: uid = user['uid'] user_id = user['user_id'] chat_id = user['chat_id'] msg_id = user['message_id']

try:
            response = requests.get(f"{LIKE_API_URL}?uid={uid}&server_name=ind")
            data = response.json()

            if str(data.get("UID", "")) != uid:
                result = "🔺️Error: Response UID doesn't match requested UID"
            elif data.get("status") == 2:
                result = (
                    f"❌ *Like Failed or Max Limit Reached*\n\n"
                    f"👤 *Player:* {data.get('PlayerNickname', 'Unknown')}\n"
                    f"🆔 *UID:* `{uid}`\n"
                    f"👍 *Likes Before:* {data.get('LikesbeforeCommand', 0)}\n"
                    f"✨ *Likes Added:* 0\n"
                    f"🇮🇳 *Total Likes Now:* {data.get('LikesafterCommand', 0)}\n"
                    f"⏰ *Tried At:* {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}"
                )
            else:
                before = data.get("LikesbeforeCommand", 0)
                after = data.get("LikesafterCommand", 0)
                added = data.get("LikesGivenByAPI", 0)
                player = data.get("PlayerNickname", "Unknown")

                result = (
                    f"✅ *LIKES SENT SUCCESSFULLY!!*\n\n"
                    f"👤 *Player:* {player}\n"
                    f"🆔 *UID:* `{uid}`\n"
                    f"🌍 *Region:* IND\n"
                    f"👍 *Likes Before:* {before}\n"
                    f"✨ *Likes Added:* {added}\n"
                    f"🇮🇳 *Total Likes Now:* {after}\n"
                    f"⏰ *Processed At:* {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}"
                )
                profiles.update_one({"user_id": user_id}, {"$set": {"last_used": datetime.utcnow()}}, upsert=True)

        except Exception as e:
            result = (
                f"❌ *API Error: Unable to process like*\n\n"
                f"🆔 *UID:* `{uid}`\n"
                f"📛 Error: {str(e)}\n"
                f"⏰ *Time:* {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}"
            )

        try:
            await app.bot.send_message(
                chat_id=chat_id,
                reply_to_message_id=msg_id,
                text=result,
                parse_mode='Markdown'
            )
        except Exception as e:
            print("Error sending message:", e)

        users.update_one({"_id": user['_id']}, {"$set": {"processed": True}})
    await asyncio.sleep(5)

def run_bot(): app = Application.builder().token(BOT_TOKEN).build() app.add_handler(CommandHandler("like", like_command)) app.add_handler(CommandHandler("givevip", givevip_command))

thread = threading.Thread(target=flask_app.run, kwargs={"host": "0.0.0.0", "port": 5000})
thread.start()

asyncio.get_event_loop().create_task(process_verified_likes(app))
app.run_polling()

if name == 'main': run_bot()

