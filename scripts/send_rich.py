#!/usr/bin/env python3

import json
import sys
from getpass import getpass
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


# Разрешён только этот канал
CHAT_ID = -1001881890472
EXPECTED_TITLE = "Dmitry Naumov"

MAX_RICH_MESSAGE_CHARS = 32768
REQUEST_TIMEOUT_SECONDS = 30


def telegram_call(api_base, method, payload=None):
    """Вызвать метод Telegram Bot API и вернуть поле result."""

    data = json.dumps(
        payload or {},
        ensure_ascii=False,
    ).encode("utf-8")

    request = Request(
        f"{api_base}/{method}",
        data=data,
        headers={
            "Content-Type": "application/json; charset=utf-8",
        },
        method="POST",
    )

    try:
        with urlopen(
            request,
            timeout=REQUEST_TIMEOUT_SECONDS,
        ) as response:
            answer = json.load(response)

    except HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")

        try:
            description = json.loads(body).get(
                "description",
                body,
            )
        except json.JSONDecodeError:
            description = body

        raise SystemExit(
            f"Telegram API, метод {method}: {description}"
        ) from None

    except (URLError, TimeoutError) as error:
        reason = getattr(error, "reason", error)

        raise SystemExit(
            f"Сетевая ошибка при вызове {method}: {reason}\n"
            "Если ошибка возникла при отправке, сначала проверьте канал: "
            "Telegram мог принять сообщение до разрыва соединения."
        ) from None

    if not answer.get("ok"):
        raise SystemExit(
            f"Telegram API, метод {method}: "
            f"{answer.get('description', 'неизвестная ошибка')}"
        )

    return answer["result"]


def read_post_file():
    """Прочитать Markdown-файл, переданный в командной строке."""

    if len(sys.argv) != 2:
        script_name = Path(sys.argv[0]).name

        raise SystemExit(
            f"Запуск: python3 {script_name} post.md"
        )

    post_path = Path(sys.argv[1]).expanduser()

    if not post_path.is_file():
        raise SystemExit(
            f"Файл не найден: {post_path}"
        )

    try:
        # utf-8-sig также корректно удалит BOM, если он есть.
        post = post_path.read_text(
            encoding="utf-8-sig",
        ).strip()

    except UnicodeDecodeError:
        raise SystemExit(
            f"Файл должен быть сохранён в UTF-8: {post_path}"
        ) from None

    if not post:
        raise SystemExit("Файл пуст.")

    if "\x00" in post:
        raise SystemExit(
            "В файле найден недопустимый нулевой символ."
        )

    char_count = len(post)

    if char_count > MAX_RICH_MESSAGE_CHARS:
        raise SystemExit(
            f"Пост слишком длинный: {char_count} символов; "
            f"предел Rich Message — {MAX_RICH_MESSAGE_CHARS}."
        )

    return post_path.resolve(), post, char_count


def main():
    # До ввода токена проверяем, что файл существует и читается.
    post_path, post, char_count = read_post_file()

    token = getpass("Токен бота: ").strip()

    if not token:
        raise SystemExit("Токен не введён.")

    api_base = f"https://api.telegram.org/bot{token}"

    # Эти три вызова ничего не публикуют.
    bot = telegram_call(
        api_base,
        "getMe",
    )

    chat = telegram_call(
        api_base,
        "getChat",
        {"chat_id": CHAT_ID},
    )

    actual_id = chat.get("id")
    actual_type = chat.get("type")
    actual_title = chat.get("title", "")

    # Независимые проверки получателя.
    if actual_id != CHAT_ID:
        raise SystemExit(
            f"Остановка: Telegram вернул chat_id {actual_id}, "
            f"ожидался {CHAT_ID}."
        )

    if actual_type != "channel":
        raise SystemExit(
            f"Остановка: chat_id {CHAT_ID} относится к типу "
            f"«{actual_type}», а не к каналу."
        )

    if actual_title != EXPECTED_TITLE:
        raise SystemExit(
            f"Остановка: канал называется «{actual_title}», "
            f"а ожидалось «{EXPECTED_TITLE}»."
        )

    # Проверяем, что именно этот бот является администратором
    # и имеет право публиковать посты.
    membership = telegram_call(
        api_base,
        "getChatMember",
        {
            "chat_id": CHAT_ID,
            "user_id": bot["id"],
        },
    )

    status = membership.get("status")

    if status not in {"administrator", "creator"}:
        raise SystemExit(
            "Остановка: бот не является администратором канала; "
            f"статус — {status!r}."
        )

    if (
        status == "administrator"
        and membership.get("can_post_messages") is not True
    ):
        raise SystemExit(
            "Остановка: у бота нет права публиковать "
            "сообщения в канале."
        )

    bot_name = (
        bot.get("username")
        or bot.get("first_name")
        or str(bot["id"])
    )

    print()

    if bot.get("username"):
        print(f"Бот: @{bot_name}")
    else:
        print(f"Бот: {bot_name}")

    print(f"Канал: {actual_title}")
    print(f"chat_id: {CHAT_ID}")
    print(f"Файл: {post_path}")
    print(f"Размер: {char_count} символов")

    # Показываем весь фактически отправляемый текст.
    print("\n----- НАЧАЛО ПОСТА -----\n")
    print(post)
    print("\n----- КОНЕЦ ПОСТА -----\n")

    expected_confirmation = f"PUBLISH {CHAT_ID}"

    confirmation = input(
        "Для публикации введите точно:\n"
        f"{expected_confirmation}\n> "
    ).strip()

    if confirmation != expected_confirmation:
        raise SystemExit(
            "Публикация отменена. Ничего не отправлено."
        )

    # Это единственное место, где происходит публикация.
    message = telegram_call(
        api_base,
        "sendRichMessage",
        {
            "chat_id": CHAT_ID,
            "rich_message": {
                "markdown": post,
            },
            "disable_notification": True,
        },
    )

    # Контроль ответа уже после публикации.
    returned_chat_id = message.get(
        "chat",
        {},
    ).get("id")

    if returned_chat_id != CHAT_ID:
        raise SystemExit(
            "Telegram сообщил об успешной отправке, "
            "но вернул неожиданный chat_id: "
            f"{returned_chat_id}."
        )

    print(
        f"Опубликовано в «{actual_title}». "
        f"message_id = {message['message_id']}"
    )


if __name__ == "__main__":
    main()
