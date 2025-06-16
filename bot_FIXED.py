
from datetime import datetime
import hashlib
import os
import time
import re
from telethon.sync import TelegramClient
from telethon.tl.functions.messages import GetHistoryRequest
from telethon.tl.types import PeerUser
from colorama import init, Fore, Style

# Initialize color output
init(autoreset=True)

# Configurable settings
CYCLE_DELAY_MIN = 15
DELAY_BETWEEN_MSGS = 5
LAST_HASH_FILE = "last_hash.txt"
GROUP_FILE = "Groups.txt"
CRED_FILE = "Credentials.txt"
LOG_FILE = "sent.log"
OWNER_ID = 7775062794

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

def process_time_command(client):
    global CYCLE_DELAY_MIN
    try:
        history = client(GetHistoryRequest(
            peer='me',
            offset_id=0,
            offset_date=None,
            add_offset=0,
            limit=10,
            max_id=0,
            min_id=0,
            hash=0
        ))
        for message in history.messages:
            if message.sender_id == OWNER_ID and message.message and message.message.startswith('.time'):
                match = re.match(r'\.time\s+(\d+)([mh]?)', message.message)
                if match:
                    value, unit = match.groups()
                    value = int(value)
                    if unit == 'h':
                        CYCLE_DELAY_MIN = value * 60
                        readable = f"{value} hour{'s' if value > 1 else ''}"
                    else:
                        CYCLE_DELAY_MIN = value
                        readable = f"{value} minute{'s' if value > 1 else ''}"
                    print(f"[Owner Command] Updated CYCLE_DELAY_MIN to {CYCLE_DELAY_MIN} minutes")
                    client.send_message('me', f"✅ Time is successfully changed to {readable}")
                    break
    except Exception as e:
        print(f"[!] Error processing .time command: {e}")

def forward_saved_messages(client):
    while True:
        try:
            process_time_command(client)
            with open(GROUP_FILE, 'r') as f:
                groups = [line.strip() for line in f if line.strip()]
            messages = client.get_messages('me', limit=100)
            for message in reversed(messages):
                for group in groups:
                    try:
                        client.forward_messages(group, message)
                        print(f"Forwarded message to {group}")
                    except Exception as e:
                        print(f"Error forwarding to {group}: {e}")
                time.sleep(CYCLE_DELAY_MIN * 60)
            print(f"Waiting for next cycle: {CYCLE_DELAY_MIN} minutes...")
            time.sleep(CYCLE_DELAY_MIN * 60)
        except Exception as e:
            print(f"Error in forward_saved_messages: {e}")
            time.sleep(60)

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

    client.connect()
    if not client.is_user_authorized():
        client.send_code_request(phone)
        code = input(Fore.RED + 'Enter the code sent to Telegram: ')
        client.sign_in(phone=phone, code=code)
    else:
        print(Fore.GREEN + '[✔] Logged in.\n')

    forward_saved_messages(client)

if __name__ == '__main__':
    main()
