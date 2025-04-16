from telethon.sync import TelegramClient

print("== Telegram Session Generator ==")
api_id = int(input("Enter your API ID: "))
api_hash = input("Enter your API HASH: ")
phone = input("Enter your phone number (with country code): ")

client = TelegramClient(phone, api_id, api_hash)
client.connect()

if not client.is_user_authorized():
    client.send_code_request(phone)
    code = input("Enter the code you received: ")
    client.sign_in(phone, code)

print(f"Session generated and saved as {phone}.session")
print("Upload this file to the bot.")

client.disconnect()

