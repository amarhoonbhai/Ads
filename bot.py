import json
import asyncio
import time
from telethon import TelegramClient, events
from telethon.sessions import StringSession

# === TELEGRAM API CREDENTIALS ===
api_id = 28464245
api_hash = '6fe23ca19e7c7870dc2aff57fb05c4d9'

# === SESSION STRING ===
# Generate it using a separate script, then paste it below:
session_string = 'User(id=7699253029, is_self=True, contact=False, mutual_contact=False, deleted=False, bot=True, bot_chat_history=False, bot_nochats=False, verified=False, restricted=False, min=False, bot_inline_geo=False, support=False, scam=False, apply_min_photo=True, fake=False, bot_attach_menu=False, premium=False, attach_menu_enabled=False, bot_can_edit=True, close_friend=False, stories_hidden=False, stories_unavailable=True, contact_require_premium=False, bot_business=False, bot_has_main_app=False, access_hash=-6512193603957157777, first_name='Spinify Mania', last_name=None, username='SpinifyBot', phone=None, photo=UserProfilePhoto(photo_id=6168103423023631237, dc_id=5, has_video=False, personal=False, stripped_thumb=None), status=None, bot_info_version=1, restriction_reason=[], bot_inline_placeholder=None, lang_code=None, emoji_status=None, usernames=[], stories_max_id=None, color=None, profile_color=None, bot_active_users=None, bot_verification_icon=None, send_paid_messages_stars=None)'

# === OWNER CONFIG ===
owner_id = 7775062794  # 👑 Your Telegram user ID (bot owner)
cooldown_minutes = 30
post_delay_seconds = cooldown_minutes * 60

# === FILE PATHS ===
GROUPS_FILE = 'groups.json'
ADS_FILE = 'ads.json'
COOLDOWN_FILE = 'cooldowns.json'

# === LOAD & SAVE HELPERS ===
def load_json(path, default):
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return default

def save_json(path, data):
    with open(path, 'w') as f:
        json.dump(data, f)

# === INITIALIZE FILE DATA ===
groups = load_json(GROUPS_FILE, [])
ads = load_json(ADS_FILE, {})
cooldowns = load_json(COOLDOWN_FILE, {})

# === INIT TELEGRAM CLIENT ===
client = TelegramClient(StringSession(session_string), api_id, api_hash)

# === /submit: Save and schedule ad ===
@client.on(events.NewMessage(pattern='/submit'))
async def submit_ad(event):
    sender = await event.get_sender()
    user_id = str(sender.id)
    now = time.time()

    # Cooldown check
    if user_id in cooldowns:
        elapsed = now - cooldowns[user_id]
        if elapsed < post_delay_seconds:
            remaining = int((post_delay_seconds - elapsed) / 60)
            await event.respond(f"⏳ Please wait {remaining} more minute(s) before submitting again.")
            return

    parts = event.raw_text.split(' ', 1)
    if len(parts) < 2:
        await event.respond("❗ Usage:\n`/submit Your ad text here...`", parse_mode='Markdown')
        return

    ad_text = parts[1]
    ads[user_id] = ad_text
    cooldowns[user_id] = now
    save_json(ADS_FILE, ads)
    save_json(COOLDOWN_FILE, cooldowns)

    await event.respond("✬ Your ad has been saved and will be auto-posted in *30 minutes*. ✬", parse_mode='Markdown')
    asyncio.create_task(schedule_post(user_id, ad_text))

# === SCHEDULE POST TO GROUPS ===
async def schedule_post(user_id, ad_text):
    await asyncio.sleep(post_delay_seconds)
    for group_id in groups:
        try:
            await client.send_message(group_id, f"📣 *New Ad Submitted!*\n\n{ad_text}", parse_mode='Markdown')
        except Exception as e:
            print(f"❌ Failed to post to group {group_id}: {e}")

# === /status: Check ad schedule (owner only) ===
@client.on(events.NewMessage(pattern='/status'))
async def check_status(event):
    sender = await event.get_sender()
    if sender.id != owner_id:
        await event.respond("🚫 This command is restricted to the bot owner.")
        return

    user_id = str(sender.id)
    ad_text = ads.get(user_id)
    if not ad_text:
        await event.respond("ℹ️ You don't have a saved ad yet.")
        return

    last_submit = cooldowns.get(user_id)
    if last_submit:
        now = time.time()
        elapsed = now - last_submit
        remaining = post_delay_seconds - elapsed

        if remaining > 0:
            mins = int(remaining // 60)
            secs = int(remaining % 60)
            await event.respond(
                f"📝 *Your Ad:*\n{ad_text}\n\n⏳ *Time Left:* {mins}m {secs}s",
                parse_mode='Markdown'
            )
        else:
            await event.respond(
                f"📝 *Your Ad:*\n{ad_text}\n\n✅ *Status:* Already Posted.",
                parse_mode='Markdown'
            )
    else:
        await event.respond("❗ No posting schedule found.")

# === /addgroup: Register current group (owner only) ===
@client.on(events.NewMessage(pattern='/addgroup'))
async def add_group(event):
    sender = await event.get_sender()
    if sender.id != owner_id:
        await event.respond("🚫 Only the bot owner can use this command.")
        return

    chat = await event.get_chat()
    if chat.id not in groups:
        groups.append(chat.id)
        save_json(GROUPS_FILE, groups)
        await event.respond("✅ This group has been added for ad posting.")
    else:
        await event.respond("ℹ️ This group is already registered.")

# === START BOT ===
async def main():
    await client.start()
    print("🤖 Ad bot is up and running.")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
