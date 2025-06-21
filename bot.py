
from datetime import datetime
import hashlib
import os
import time
import re
import asyncio
from telethon.sync import TelegramClient
from telethon.tl.functions.messages import GetHistoryRequest
from telethon.tl.types import PeerUser
from telethon import events
from telethon.errors import SessionPasswordNeededError
from colorama import init, Fore, Style

# Initialize color output
init(autoreset=True)

CYCLE_DELAY_MIN = 15
DELAY_BETWEEN_MSGS = 5
LAST_HASH_FILE = "last_hash.txt"
GROUP_FILE = "Groups.txt"
CRED_FILE = "Credentials.txt"
LOG_FILE = "sent.log"
OWNER_ID = 7876302875

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def display_banner():
    print(Fore.CYAN + r'''
     ____        _      __             _               ____        _   
    |  _ \  __ _| |_ __/ _| ___  _ __ | |__   ___ _ __|  _ \  __ _| |_ 
    | | | |/ _` | __|_  / / _ \| '_ \| '_ \ / _ \ '__| | | |/ _` | __|
    | |_| | (_| | |_ / /| (_) | | | | | | | |  __/ |  | |_| | (_| | |_ 
    |____/ \__,_|\__/___|\___/|_| |_|_| |_|\___|_|  |____/ \__,_|\__|

    ''')
    print(Style.RESET_ALL)
    print(Fore.GREEN + "📢 Auto Ad Forwarder Bot - Repeats until updated\n")

def check_and_create_files():
    if not os.path.exists(CRED_FILE): open(CRED_FILE, 'w').close()
    if not os.path.exists(GROUP_FILE): open(GROUP_FILE, 'w').close()

def save_credentials(api_id, api_hash, phone):
    with open(CRED_FILE, 'w') as f:
        f.write(f'{api_id}\n{api_hash}\n{phone}')
    print(Fore.GREEN + '[✔] Credentials saved.\n')

def load_credentials():
    if not os.path.exists(CRED_FILE): return None
    with open(CRED_FILE, 'r') as f:
        lines = f.readlines()
    return (lines[0].strip(), lines[1].strip(), lines[2].strip()) if len(lines) >= 3 else None

def load_group_urls():
    if not os.path.exists(GROUP_FILE): return []
    with open(GROUP_FILE, 'r') as f:
        return [line.strip() for line in f if line.strip()]

def get_message_hash(msg):
    content = msg.message or ''
    media_id = str(msg.media.document.id) if msg.media and hasattr(msg.media, 'document') else ''
    combined = content + media_id
    return hashlib.sha256(combined.encode()).hexdigest()

def load_last_hash():
    if os.path.exists(LAST_HASH_FILE):
        with open(LAST_HASH_FILE, 'r') as f:
            return f.read().strip()
    return ''

def save_last_hash(hash_value):
    with open(LAST_HASH_FILE, 'w') as f:
        f.write(hash_value)

def log_post(content):
    with open(LOG_FILE, 'a') as log:
        log.write(f"{datetime.now().isoformat()} - Sent ad:\n{content}\n\n")


async def forward_saved_messages(client):
    while True:
        try:
            with open(GROUP_FILE, 'r') as f:
                groups = [line.strip() for line in f if line.strip()]

            messages = await client.get_messages('me', limit=100)
            messages = list(reversed(messages))

            if not messages:
                print("No saved messages to forward.")
                await asyncio.sleep(CYCLE_DELAY_MIN * 60)
                continue

            for message in messages:
                if message.message is None and not message.media:
                    continue

                for group in groups:
                    try:
                        await client.forward_messages(group, message)
                        print(f"Forwarded message to {group}")
                    except Exception as e:
                        print(f"Error forwarding to {group}: {e}")

                log_post(message.message or "Media Message")
                await asyncio.sleep(DELAY_BETWEEN_MSGS)

            print(f"Finished cycle. Waiting {CYCLE_DELAY_MIN} minutes...")
            await asyncio.sleep(CYCLE_DELAY_MIN * 60)

        except Exception as e:
            print(f"Error in forward_saved_messages: {e}")
            await asyncio.sleep(60)



async def main_async(client):
    @client.on(events.NewMessage)
    async def handler(event):
        global CYCLE_DELAY_MIN, DELAY_BETWEEN_MSGS

        if event.sender_id != OWNER_ID:
            return

        text = event.raw_text.strip()

        if text.startswith('.time'):
            match = re.match(r'\.time\s+(\d+)([mh]?)', text)
            if match:
                value, unit = match.groups()
                value = int(value)
                if unit == 'h':
                    CYCLE_DELAY_MIN = value * 60
                else:
                    CYCLE_DELAY_MIN = value
                await event.respond(f"✅ Cycle delay updated to {value}{unit or 'm'}")

        elif text.startswith('.delay'):
            match = re.match(r'\.delay\s+(\d+)', text)
            if match:
                DELAY_BETWEEN_MSGS = int(match.group(1))
                await event.respond(f"✅ Delay between messages set to {DELAY_BETWEEN_MSGS} seconds")

        elif text.startswith('.status'):
            await event.respond(
                f"📊 Bot Status:\n"
                f"Cycle Delay: {CYCLE_DELAY_MIN} minutes\n"
                f"Message Delay: {DELAY_BETWEEN_MSGS} seconds"
            )

    await client.start()
    print(Fore.GREEN + '[✔] Bot started.\n')
    await forward_saved_messages(client)





async def main_async(client, phone):
    @client.on(events.NewMessage)
    async def handler(event):
        global CYCLE_DELAY_MIN, DELAY_BETWEEN_MSGS

        if event.sender_id != OWNER_ID:
            return

        text = event.raw_text.strip()

        if text.startswith('.time'):
            match = re.match(r'\.time\s+(\d+)([mh]?)', text)
            if match:
                value, unit = match.groups()
                value = int(value)
                if unit == 'h':
                    CYCLE_DELAY_MIN = value * 60
                else:
                    CYCLE_DELAY_MIN = value
                await event.respond(f"✅ Cycle delay updated to {value}{unit or 'm'}")

        elif text.startswith('.delay'):
            match = re.match(r'\.delay\s+(\d+)', text)
            if match:
                DELAY_BETWEEN_MSGS = int(match.group(1))
                await event.respond(f"✅ Delay between messages set to {DELAY_BETWEEN_MSGS} seconds")

        elif text.startswith('.status'):
            await event.respond(
                f"📊 Bot Status:\n"
                f"Cycle Delay: {CYCLE_DELAY_MIN} minutes\n"
                f"Message Delay: {DELAY_BETWEEN_MSGS} seconds"
            )

    await client.connect()
    if not await client.is_user_authorized():
        await client.send_code_request(phone)
        code = input(Fore.RED + 'Enter the code sent to Telegram: ')
        try:
            await client.sign_in(phone=phone, code=code)
        except SessionPasswordNeededError:
            password = input(Fore.YELLOW + 'Enter your 2FA password: ')
            await client.sign_in(password=password)
    else:
        print(Fore.GREEN + '[✔] Logged in.\n')

    print(Fore.GREEN + '[✔] Bot started.\n')

    await asyncio.gather(
        forward_saved_messages(client),
        client.run_until_disconnected()
    )


def main():
    clear_screen()
    display_banner()
    check_and_create_files()

    creds = load_credentials()
    if creds:
        reuse = input(Fore.YELLOW + '[?] Reuse last account? (yes/no): ').strip().lower()
        if reuse == 'yes':
            api_id, api_hash, phone = creds
        else:
            api_id = input(Fore.YELLOW + 'API ID: ')
            api_hash = input(Fore.YELLOW + 'API HASH: ')
            phone = input(Fore.YELLOW + 'Phone number (with country code): ')
            save_credentials(api_id, api_hash, phone)
    else:
        api_id = input(Fore.YELLOW + 'API ID: ')
        api_hash = input(Fore.YELLOW + 'API HASH: ')
        phone = input(Fore.YELLOW + 'Phone number (with country code): ')
        save_credentials(api_id, api_hash, phone)

    session_file = f'{phone}.session'
    client = TelegramClient(session_file, api_id, api_hash)

    asyncio.run(main_async(client, phone))
