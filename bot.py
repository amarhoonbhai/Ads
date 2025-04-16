import os
import json
import asyncio
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from telethon.sync import TelegramClient

OWNER_ID = 7222795580
GROUP_FILE = "data/groups.json"
os.makedirs("data", exist_ok=True)
os.makedirs("sessions", exist_ok=True)

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

def plan_limits(user_id, plan):
    if user_id == OWNER_ID:
        return {"groups": float("inf"), "delay": 0, "auto": True}
    return {
        "Basic": {"groups": 10, "delay": 30, "auto": False},
        "Pro": {"groups": 50, "delay": 10, "auto": True},
        "Elite": {"groups": 9999, "delay": 1, "auto": True}
    }.get(plan, {"groups": 10, "delay": 30, "auto": False})

async def is_owner(update):
    return update.effective_user.id == OWNER_ID

async def is_approved(update):
    user_id = update.effective_user.id
    profile = load_user_profile(user_id)
    return profile.get("approved", False) or user_id == OWNER_ID

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Upload Session", callback_data="upload"),
         InlineKeyboardButton("Set Message", callback_data="change")],
        [InlineKeyboardButton("Send", callback_data="send"),
         InlineKeyboardButton("My Plan", callback_data="plan")],
        [InlineKeyboardButton("Add Group", callback_data="addgroup"),
         InlineKeyboardButton("List Groups", callback_data="listgroups")]
    ]
    await update.message.reply_text(
        "*Welcome To Spinify Advertise Bot!*\n\n"
        "*Quick Commands:*\n"
        "`/upload` - Upload your session\n"
        "`/change` - Set your ad message\n"
        "`/send` - Send message to all groups\n"
        "`/plan` - View current plan\n"
        "`/addgroup` - Add a new group\n\n"
        "Use the buttons below to navigate.\n\n"
        "*Developer:* @Spinify",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text("Usage: /upload <session_string>")
        return
    session_data = context.args[0]
    try:
        with open(f"sessions/{user_id}.session", "w") as f:
            f.write(session_data)
        await update.message.reply_text("✅ Session uploaded successfully.")
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to save session: {e}")

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

async def send(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    limit = plan_limits(user_id, plan)
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

async def plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_approved(update):
        await update.message.reply_text("Not approved.")
        return
    user_id = update.effective_user.id
    profile = load_user_profile(user_id)
    plan = profile.get("plan", "Basic")
    limits = plan_limits(user_id, plan)
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
    min_delay = plan_limits(user_id, profile.get("plan", "Basic"))["delay"]
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
    if not context.args:
        await update.message.reply_text("Usage: /approve <user_id>")
        return
    uid = int(context.args[0])
    profile = load_user_profile(uid)
    profile["approved"] = True
    save_user_profile(uid, profile)
    await update.message.reply_text(f"✅ User {uid} approved.")

async def upgrade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_owner(update):
        await update.message.reply_text("Only owner can upgrade plans.")
        return
    if len(context.args) != 2:
        await update.message.reply_text("Usage: /upgrade <amount> <user_id>")
        return
    amount, uid = context.args
    uid = int(uid)
    plan_map = {"10$": "Basic", "25$": "Pro", "50$": "Elite"}
    plan = plan_map.get(amount)
    if not plan:
        await update.message.reply_text("Invalid amount. Use 10$, 25$, or 50$")
        return
    profile = load_user_profile(uid)
    profile["plan"] = plan
    save_user_profile(uid, profile)
    await update.message.reply_text(f"✅ Upgraded user {uid} to {plan} plan.")

if __name__ == "__main__":
    print(">> Telegram Bot is starting...")
    bot_token = "8062232378:AAHptyCOvgTftXu0JOJB4Md_IC9g9YfPdXA"
    app = ApplicationBuilder().token(bot_token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("upload", upload))
    app.add_handler(CommandHandler("change", change))
    app.add_handler(CommandHandler("send", send))
    app.add_handler(CommandHandler("plan", plan))
    app.add_handler(CommandHandler("setdelay", setdelay))
    app.add_handler(CommandHandler("addgroup", addgroup))
    app.add_handler(CommandHandler("listgroups", listgroups))
    app.add_handler(CommandHandler("approve", approve))
    app.add_handler(CommandHandler("upgrade", upgrade))

    print(">> Bot is now running. Use Ctrl+C to stop.")
    app.run_polling()
