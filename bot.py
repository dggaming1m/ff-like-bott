import os
import json
import requests
import datetime

from telegram import Update, InputFile
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from github import Github, GithubException

# Configuration
TELEGRAM_TOKEN = "7491481953:AAEEE_QN9emVhFGXdfTpS2KUQCtdovOlWdk"
TOKEN_API = "https://uditanshu-jwt.vercel.app/token?uid={uid}&password={password}"

# User data storage
user_data = {}

class User:
    def __init__(self, user_id):
        self.user_id = user_id
        self.github_token = None
        self.repository = None
        self.target_file = None
        self.guest_accounts = []
        self.generated_tokens = []
        self.setup_step = 0  # 0=not started, 1=token, 2=repo, 3=file, 4=accounts

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_data:
        user_data[user_id] = User(user_id)
    await update.message.reply_text(
        "👋 Welcome to the Token Manager Bot!\n\n"
        "🔹 Use /newuser to set up your account\n"
        "🔹 Use /token to generate tokens\n"
        "🔹 Use /updatetoken to update GitHub\n"
        "🔹 Use /delete to remove your data\n"
        "Owner: @LipuGaming_ff"
    )

async def newuser_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if update.message.chat.type != "private":
        await update.message.reply_text("⚠️ Please use this command in private messages (DMs).")
        return
    user_data[user_id] = User(user_id)
    user = user_data[user_id]
    user.setup_step = 1
    await update.message.reply_text(
        "🆕 New user setup started!\n\n"
        "1. Please send your GitHub personal access token:"
    )

async def handle_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_data:
        return
    user = user_data[user_id]
    text = update.message.text.strip() if update.message and update.message.text else ""
    if user.setup_step == 1:
        user.github_token = text
        user.setup_step = 2
        await update.message.reply_text(
            "✅ GitHub token saved!\n\n"
            "2. Now send your repository name in format: owner/repo\n"
            "Example: glxsyy-akash/Ultimate"
        )
    elif user.setup_step == 2:
        if '/' not in text:
            await update.message.reply_text("⚠️ Invalid format. Please use: owner/repo")
            return
        user.repository = text
        user.setup_step = 3
        await update.message.reply_text(
            "✅ Repository saved!\n\n"
            "3. Now send the target JSON filename (must end with .json)\n"
            "Example: token_ind.json"
        )
    elif user.setup_step == 3:
        if not text.lower().endswith('.json'):
            await update.message.reply_text("⚠️ File must end with .json")
            return
        user.target_file = text
        user.setup_step = 4
        await update.message.reply_text(
            "✅ Target file saved!\n\n"
            "4. Now UPLOAD your guest accounts .json file in this EXACT format:\n\n"
            "[\n"
            '    {\n'
            '        "uid": "3745752307",\n'
            '        "password": "YOUR_PASSWORD_HASH"\n'
            '    }\n'
            "]"
        )

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_data:
        return
    user = user_data[user_id]
    if user.setup_step != 4:
        return
    document = update.message.document
    if not document.file_name.endswith('.json'):
        await update.message.reply_text("⚠️ File must be a .json file!")
        return
    file = await context.bot.get_file(document.file_id)
    file_data = await file.download_as_bytearray()
    try:
        accounts = json.loads(file_data.decode('utf-8'))
        if not isinstance(accounts, list):
            raise ValueError("Must be an array of accounts")
        for account in accounts:
            if not isinstance(account, dict):
                raise ValueError("Each account must be an object")
            if "uid" not in account or "password" not in account:
                raise ValueError("Each account must have uid and password")
            if not isinstance(account["uid"], str) or not isinstance(account["password"], str):
                raise ValueError("UID and password must be strings")
        user.guest_accounts = accounts
        user.setup_step = 0
        await update.message.reply_text(
            "✅ Guest accounts validated and saved!\n\n"
            "Setup complete! You can now:\n"
            "• Generate tokens with /token\n"
            "• Update GitHub with /updatetoken"
        )
    except Exception as e:
        await update.message.reply_text(
            f"⚠️ Invalid file format. Error: {str(e)}\n\n"
            "Please upload a .json file in EXACTLY this format:\n\n"
            "[\n"
            '    {\n'
            '        "uid": "3745752307",\n'
            '        "password": "YOUR_PASSWORD_HASH"\n'
            '    }\n'
            "]"
        )

async def token_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_data:
        await update.message.reply_text("⚠️ Please use /newuser first to set up your account.")
        return
    user = user_data[user_id]
    if not user.guest_accounts:
        await update.message.reply_text("⚠️ No guest accounts found. Please complete setup with /newuser.")
        return
    try:
        await update.message.reply_text("🔑 Generating tokens from guest accounts...")
        user.generated_tokens = []
        for account in user.guest_accounts:
            uid = account["uid"]
            password = account["password"]
            try:
                response = requests.get(TOKEN_API.format(uid=uid, password=password))
                if response.status_code == 200:
                    new_token = response.json().get("token", "")
                    if new_token:
                        user.generated_tokens.append(new_token)
                        await update.message.reply_text(f"✅ Token generated for UID: {uid}")
                    else:
                        await update.message.reply_text(f"⚠️ Empty token received for UID: {uid}")
                else:
                    await update.message.reply_text(f"❌ Failed to generate token for UID: {uid} (Status: {response.status_code})")
            except Exception as e:
                await update.message.reply_text(f"⚠️ Error processing UID {uid}: {str(e)}")
        if user.generated_tokens:
            await update.message.reply_text(
                f"🎉 Successfully generated {len(user.generated_tokens)} tokens!\n"
                "Use /updatetoken to update them on GitHub."
            )
        else:
            await update.message.reply_text("⚠️ No tokens were generated from the provided accounts.")
    except Exception as e:
        await update.message.reply_text(f"❌ Critical error during token generation: {str(e)}")

async def update_token_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_data:
        await update.message.reply_text("⚠️ Please use /newuser first to set up your account.")
        return
    user = user_data[user_id]
    if not user.generated_tokens:
        await update.message.reply_text("⚠️ No tokens generated yet. Use /token first.")
        return
    if not user.github_token:
        await update.message.reply_text("⚠️ Missing GitHub token. Please set up with /newuser.")
        return
    if not user.repository or not user.target_file:
        await update.message.reply_text("⚠️ Incomplete setup. Please complete with /newuser.")
        return
    try:
        await update.message.reply_text("🔄 Attempting to update tokens on GitHub...")
        g = Github(user.github_token)
        repo = g.get_repo(user.repository)
        token_data = [{"token": token} for token in user.generated_tokens]
        try:
            file_content = repo.get_contents(user.target_file)
            repo.update_file(
                user.target_file,
                "Updated tokens via bot",
                json.dumps(token_data, indent=2),
                file_content.sha
            )
            action = "updated"
        except:
            repo.create_file(
                user.target_file,
                "Created tokens via bot",
                json.dumps(token_data, indent=2)
            )
            action = "created"
        await update.message.reply_text(
            f"✅ {len(user.generated_tokens)} tokens successfully {action} in {user.target_file}!\n"
            f"Repository: {user.repository}\n"
            "Stored in exact format:\n"
            "[\n"
            '  {"token": "..."},\n'
            '  {"token": "..."}\n'
            "]"
        )
        user.generated_tokens = []
    except GithubException as ge:
        await update.message.reply_text(
            f"❌ GitHub API Error:\nStatus: {ge.status}\nMessage: {str(ge)}"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Critical error during GitHub update: {str(e)}")

async def delete_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if update.message.chat.type != "private":
        await update.message.reply_text("⚠️ Please use this command in private messages (DMs).")
        return
    if user_id in user_data:
        del user_data[user_id]
        await update.message.reply_text(
            "🗑️ All your data has been deleted.\nYou can start fresh with /newuser if needed."
        )
    else:
        await update.message.reply_text("ℹ️ No user data found to delete.")

def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("newuser", newuser_command))
    application.add_handler(CommandHandler("token", token_command))
    application.add_handler(CommandHandler("updatetoken", update_token_command))
    application.add_handler(CommandHandler("delete", delete_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_messages))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    print("✅ Bot is running... Owner-@LipuGaming_ff")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()