from telethon import TelegramClient, connection
from telethon.errors import SessionPasswordNeededError
from telethon.tl.functions.account import GetAuthorizationsRequest
from config import API_ID, API_HASH
import os
import json
import asyncio
import socks, sys

# Путь к файлам с номерами телефонов и прокси
SESSIONS_FILE = 'sessions.txt'
PROXY_FILE = 'proxy.txt'
SESSIONS_DIR = 'sessions'

# Убедимся, что директория сессий существует
if not os.path.exists(SESSIONS_DIR):
    os.makedirs(SESSIONS_DIR)


def load_proxy():
    with open(PROXY_FILE, 'r') as f:
        proxy_line = f.readline().strip()
        proxy_data = proxy_line.split(":")
        proxy_type = proxy_data[0]

        if proxy_type == "proxy.mtproto.ru":
            host, port, secret = proxy_data
            return {"type": "MTPROTO", "connection_cortege": (host, int(port), secret), "connection": connection.ConnectionTcpMTProxyRandomizedIntermediate}

        elif proxy_type == "http":
            proxy_type, host, port, user, password = proxy_data
            return {"type": "HTTP",  "connection_cortege": (socks.HTTP, host, int(port), True, user, password)}

        elif proxy_type == "socks5":
            proxy_type, host, port, user, password = proxy_data
            return {"type": "SOCKS5",  "connection_cortege": (socks.SOCKS5, host, int(port), True, user, password)}

        return {"type": "ERROR"}


def load_phones():
    with open(SESSIONS_FILE, 'r') as f:
        return [phone.strip() for phone in f.readlines()]


def save_session(phone, two_fa, proxy, proxy_type):
    session_file_json = os.path.join(SESSIONS_DIR, f'{phone}.json')
    session_data = {
        'app_id': int(API_ID),
        'app_hash': API_HASH,
        'two_fa': two_fa,
        'proxy': proxy,
        'proxy_type': proxy_type
    }

    with open(session_file_json, 'w') as f:
        json.dump(session_data, f, indent=4)


def phone_validation(phone):
    phone = phone.replace("+", "")
    phone = phone.replace(" ", "")

    return phone


async def create_session(phone, proxy):
    print(f"Работаем с {phone}...")

    phone = phone_validation(phone=phone)

    if (proxy.get("type") == "MTPROTO"):
        client = TelegramClient(os.path.join(
            SESSIONS_DIR, phone), API_ID, API_HASH, proxy=proxy.get("connection_cortege"), connection=proxy.get("connection"))
    else:
        client = TelegramClient(os.path.join(
            SESSIONS_DIR, phone), API_ID, API_HASH, proxy=proxy.get("connection_cortege"))

    await client.start(phone)

    try:
        # Если требуется пароль 2FA
        if await client.is_user_authorized() is False:
            print("Введите код, отправленный на номер:")
            code = input('Код: ')
            await client.sign_in(phone, code)

        if await client.is_user_authorized() is False:
            try:
                password = input('Введите 2FA пароль: ')
                await client.sign_in(password=password)
                two_fa = password
            except SessionPasswordNeededError:
                print("Нужен 2FA пароль")
                return False
        else:
            two_fa = None

        print(f"Сессия для {phone} успешно создана!")
        save_session(phone, two_fa, proxy.get("connection_cortege"), proxy.get("type"))

    except Exception as e:
        print(f"Ошибка при создании сессии для {phone}: {e}")

    finally:
        await client.disconnect()


async def main():
    phones = load_phones()

    proxy = load_proxy()
    if (proxy.get("type") == "ERROR"):
        print("Ошибка, прокси не корректны")
        sys.exit(1)

    for phone in phones:
        await create_session(phone, proxy)

if __name__ == "__main__":
    asyncio.run(main())
