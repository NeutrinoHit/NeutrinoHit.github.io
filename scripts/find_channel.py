import json
from datetime import datetime
from getpass import getpass
from urllib.request import Request, urlopen

token = getpass("Токен бота: ").strip()

payload = {
    "limit": 100,
    "timeout": 0,
    "allowed_updates": ["channel_post"],
}

request = Request(
    f"https://api.telegram.org/bot{token}/getUpdates",
    data=json.dumps(payload).encode("utf-8"),
    headers={"Content-Type": "application/json"},
)

with urlopen(request) as response:
    result = json.load(response)

if not result["ok"]:
    raise RuntimeError(result["description"])

updates = [
    update
    for update in result["result"]
    if "channel_post" in update
]

if not updates:
    raise SystemExit(
        "Новых сообщений канала не найдено. "
        "Опубликуйте обычное сообщение в тестовом канале и запустите скрипт снова."
    )

last_update = max(updates, key=lambda update: update["update_id"])
post = last_update["channel_post"]
chat = post["chat"]

content = (
    post.get("text")
    or post.get("caption")
    or "[сообщение без обычного текста]"
)

date = datetime.fromtimestamp(post["date"]).astimezone()

print()
print(f"Канал: {chat.get('title', 'Без названия')}")
print(f"chat_id: {chat['id']}")
print(f"message_id: {post['message_id']}")
print(f"Дата: {date:%Y-%m-%d %H:%M:%S %Z}")
print("Последнее сообщение:")
print(content)
