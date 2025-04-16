# Full version of bot.py combining all features and including startup logs
import os
import json
import asyncio
from telegram import Update, Document
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters,
    ContextTypes
)
from telethon.sync import TelegramClient
from telethon.tl.functions.messages import GetHistoryRequest

OWNER_ID = 7222795580
GROUP_FILE = "data/groups.json"
os.makedirs("data", exist_ok=True)
os.makedirs("sessions", exist_ok=True)
user_tasks = {}

def get_user_dir(user_id):
    path = f"data/{user_id}"
    os.makedirs(path, exist_ok=True)
    return path

def load_user_profile(user_id):
    path = f"{get_user_dir(user_id)}/profile.json"
    if not os.path.exists(path):
        return {"approved": False, "plan": "Basic", "delay": 30}
    with open(path) as f:
        return json.load(f)

def save_user_profile(user_id, data):
    with open(f"{get_user_dir(user_id)}/profile.json", 'w') as f:
        json.dump(data, f)

def load_groups():
    if not os.path.exists(GROUP_FILE):
        return []
    with open(GROUP_FILE) as f:
        return json.load(f)

def save_groups(groups):
    with open(GROUP_FILE, 'w') as f:
        json.dump(groups, f)

def plan_limits(plan):
    return {
        "Basic": {"groups": 10, "delay": 30, "auto": False},
        "Pro": {"groups": 50, "delay": 10, "auto": True},
        "Elite": {"groups": 9999, "delay": 1, "auto": True},
        "Owner": {"groups": 9999, "delay": 1, "auto": True},
    }.get(plan, {"groups": 10, "delay": 30, "auto": False})

async def is_owner(update):
    return update.effective_user.id == OWNER_ID

async def is_approved(update):
    user_id = update.effective_user.id
    profile = load_user_profile(user_id)
    return profile.get("approved", False) or user_id == OWNER_ID

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    await update.message.reply_text(
        f"Welcome to the Multi-User Forward Bot!\nYour ID: `{uid}`\n"
        "Commands:\n"
        "/uploadsession – Upload your .session file\n"
        "/change <message> – Set your message\n"
        "/sendall – Send to all groups\n"
        "/setdelay <sec>\n"
        "/plan – View your current plan\n"
        "/addgroup <url>\n"
        "/listgroups\n"
        "\nAdmins:\n"
        "/approve <user_id>\n"
        "/upgrade <amount> <user_id>"
    )

async def upload_session(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc: Document = update.message.document
    if not doc or not doc.file_name.endswith(".session"):
        await update.message.reply_text("Please upload a .session file.")
        return
    file = await context.bot.get_file(doc.file_id)
    dest = f"sessions/{update.effective_user.id}.session"
    await file.download_to_drive(dest)
    await update.message.reply_text("Session saved.")

async def change(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_approved(update):
        await update.message.reply_text("Not approved. Contact admin.")
        return
    user_id = update.effective_user.id
    msg = " ".join(context.args)
    if not msg:
        await update.message.reply_text("Usage: /change Your message here")
        return
    profile = load_user_profile(user_id)
    profile["message"] = msg
    save_user_profile(user_id, profile)
    await update.message.reply_text("Message saved.")

async def sendall(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_approved(update):
        await update.message.reply_text("Not approved.")
        return
    user_id = update.effective_user.id
    session_file = f"sessions/{user_id}.session"
    if not os.path.exists(session_file):
        await update.message.reply_text("No session uploaded.")
        return
    profile = load_user_profile(user_id)
    message = profile.get("message")
    if not message:
        await update.message.reply_text("No message set. Use /change.")
        return
    delay = profile.get("delay", 30)
    plan = profile.get("plan", "Basic")
    limit = plan_limits(plan)
    groups = load_groups()
    if len(groups) > limit["groups"]:
        await update.message.reply_text("Group limit exceeded.")
        return
    try:
        client = TelegramClient(session_file, 1, 'abc')
        await client.start()
        for g in groups:
            try:
                await client.send_message(g, message)
                await update.message.reply_text(f"Sent to {g}")
                await asyncio.sleep(delay)
            except Exception as e:
                await update.message.reply_text(f"Error sending to {g}: {e}")
        await client.disconnect()
    except Exception as e:
        await update.message.reply_text(f"Session error: {e}")

async def auto_send_loop(user_id, context):
    session_file = f"sessions/{user_id}.session"
    if not os.path.exists(session_file):
        return
    profile = load_user_profile(user_id)
    plan = profile.get("plan", "Basic")
    if not plan_limits(plan)["auto"]:
        return
    delay = profile.get("delay", 30)
    message = profile.get("message")
    if not message:
        return
    groups = load_groups()
    try:
        client = TelegramClient(session_file, 1, 'abc')
        await client.start()
        while user_id in user_tasks:
            for g in groups:
                try:
                    await client.send_message(g, message)
                    await context.bot.send_message(user_id, f"Auto-sent to {g}")
                    await asyncio.sleep(delay)
                except Exception as e:
                    await context.bot.send_message(user_id, f"Error sending to {g}: {e}")
            await asyncio.sleep(delay)
    except Exception as e:
        await context.bot.send_message(user_id, f"Session error: {e}")
    finally:
        await client.disconnect()

async def autostart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await is_approved(update):
        await update.message.reply_text("Not approved.")
        return
    if user_id in user_tasks:
        await update.message.reply_text("Auto sending is already running.")
        return
    profile = load_user_profile(user_id)
    plan = profile.get("plan", "Basic")
    if not plan_limits(plan)["auto"]:
        await update.message.reply_text("Your plan does not support auto sending.")
        return
    task = asyncio.create_task(auto_send_loop(user_id, context))
    user_tasks[user_id] = task
    await update.message.reply_text("Auto sending started.")

async def autostop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    task = user_tasks.get(user_id)
    if not task:
        await update.message.reply_text("No auto sending task running.")
        return
    task.cancel()
    del user_tasks[user_id]
    await update.message.reply_text("Auto sending stopped.")

async def plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_approved(update):
        await update.message.reply_text("Not approved.")
        return
    user_id = update.effective_user.id
    profile = load_user_profile(user_id)
    plan = profile.get("plan", "Basic")
    limits = plan_limits(plan)
    msg = (
        f"Your Plan: {plan}\n"
        f"Group Limit: {limits['groups']}\n"
        f"Min Delay: {limits['delay']}s\n"
        f"Auto Forward: {'Yes' if limits['auto'] else 'No'}\n"
        f"Delay: {profile.get('delay', 30)}s\n"
        f"Message: {profile.get('message', 'None')[:40]}..."
    )
    await update.message.reply_text(msg)

async def setdelay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_approved(update):
        await update.message.reply_text("Not approved.")
        return
    user_id = update.effective_user.id
    delay = int(context.args[0])
    profile = load_user_profile(user_id)
    min_delay = plan_limits(profile.get("plan", "Basic"))["delay"]
    if delay < min_delay:
        await update.message.reply_text(f"Minimum delay for your plan is {min_delay}s")
        return
    profile["delay"] = delay
    save_user_profile(user_id, profile)
    await update.message.reply_text(f"Delay set to {delay}s")

async def addgroup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_approved(update):
        await update.message.reply_text("Not approved.")
        return
    if not context.args:
        await update.message.reply_text("Usage: /addgroup <link>")
        return
    groups = load_groups()
    new = context.args[0]
    if new not in groups:
        groups.append(new)
        save_groups(groups)
        await update.message.reply_text("Group added.")
    else:
        await update.message.reply_text("Already exists.")

async def listgroups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    groups = load_groups()
    await update.message.reply_text("\n".join(groups) if groups else "No groups yet.")

async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_owner(update):
        await update.message.reply_text("Only owner can approve users.")
        return
    uid = int(context.args[0])
    profile = load_user_profile(uid)
    profile["approved"] = True
    save_user_profile(uid, profile)
    await update.message.reply_text(f"User {uid} approved.")

async def upgrade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_owner(update):
        await update.message.reply_text("Only owner can upgrade plans.")
        return
    amount, uid = context.args
    uid = int(uid)
    plan_map = {"10$": "Basic", "25$": "Pro", "50$": "Elite"}
    plan = plan_map.get(amount)
    if not plan:
        await update.message.reply_text("Invalid amount. Use 10$, 25$, 50$")
        return
    profile = load_user_profile(uid)
    profile["plan"] = plan
    save_user_profile(uid, profile)
    await update.message.reply_text(f"Upgraded user {uid} to {plan}")

if __name__ == "__main__":
    print(">> Telegram Bot is starting...")

    bot_token = "8062232378:AAFCR4vtDxtqYTMZoyR_6md7QUR48MSkh3Q"
    app = ApplicationBuilder().token(bot_token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("change", change))
    app.add_handler(CommandHandler("sendall", sendall))
    app.add_handler(CommandHandler("plan", plan))
    app.add_handler(CommandHandler("setdelay", setdelay))
    app.add_handler(CommandHandler("addgroup", addgroup))
    app.add_handler(CommandHandler("listgroups", listgroups))
    app.add_handler(CommandHandler("approve", approve))
    app.add_handler(CommandHandler("upgrade", upgrade))
    app.add_handler(CommandHandler("autostart", autostart))
    app.add_handler(CommandHandler("autostop", autostop))
    app.add_handler(MessageHandler(filters.Document.ALL, upload_session))

    print(">> Bot is now running. Use Ctrl+C to stop.")
    app.run_polling()
