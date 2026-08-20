#!/usr/bin/env python3

import argparse
import json
import os
import shutil
import subprocess
import sys
from getpass import getpass
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


TEST_CHAT_ID = -1001881890472
TEST_CHAT_LABEL = "Dmitry Naumov"

FINAL_CHAT = "@NeutrinoHit"
FINAL_USERNAME = "NeutrinoHit"

MAX_RICH_MESSAGE_CHARS = 32768
REQUEST_TIMEOUT_SECONDS = 30

TOKEN_ENV_NAME = "TELEGRAM_BOT_TOKEN"
KEYCHAIN_SERVICE = "NeutrinoHit Telegram Bot"
KEYCHAIN_ACCOUNT = "send_rich.py"


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Отправить Markdown как Telegram Rich Message. "
            "Без указания режима используется безопасный тестовый канал."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Примеры:\n"
            "  python3 scripts/send_rich.py --test post.md\n"
            "  python3 scripts/send_rich.py --final post.md\n"
            "  python3 scripts/send_rich.py --final --yes post.md\n"
            "  python3 scripts/send_rich.py --store-token\n"
        ),
    )

    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--test",
        dest="mode",
        action="store_const",
        const="test",
        help=(
            f"отправить в тестовый канал «{TEST_CHAT_LABEL}» "
            "без проверок и подтверждения (режим по умолчанию)"
        ),
    )
    mode.add_argument(
        "--final",
        dest="mode",
        action="store_const",
        const="final",
        help=(
            f"отправить финальный пост в {FINAL_CHAT} "
            "после проверки канала и прав бота"
        ),
    )
    parser.set_defaults(mode="test")

    parser.add_argument(
        "--yes",
        action="store_true",
        help="в финальном режиме не спрашивать короткое подтверждение",
    )
    parser.add_argument(
        "--notify",
        action="store_true",
        help="отправить пост с уведомлением подписчикам",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="показать файл и режим, ничего не отправляя и не запрашивая токен",
    )
    parser.add_argument(
        "--store-token",
        action="store_true",
        help="проверить и сохранить новый токен в macOS Keychain",
    )
    parser.add_argument(
        "--forget-token",
        action="store_true",
        help="удалить сохранённый токен из macOS Keychain",
    )
    parser.add_argument(
        "post",
        nargs="?",
        type=Path,
        help="Markdown-файл с постом",
    )

    args = parser.parse_args()

    maintenance_actions = int(args.store_token) + int(args.forget_token)

    if maintenance_actions > 1:
        parser.error("--store-token и --forget-token нельзя использовать вместе")

    if maintenance_actions and args.post is not None:
        parser.error("для работы с токеном Markdown-файл указывать не нужно")

    if not maintenance_actions and args.post is None:
        parser.error("укажите Markdown-файл с постом")

    if args.mode == "test" and args.yes:
        parser.error("--yes нужен только вместе с --final")

    return args


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


def keychain_available():
    return sys.platform == "darwin" and shutil.which("security") is not None


def read_keychain_token():
    if not keychain_available():
        return None

    result = subprocess.run(
        [
            "security",
            "find-generic-password",
            "-a",
            KEYCHAIN_ACCOUNT,
            "-s",
            KEYCHAIN_SERVICE,
            "-w",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        return None

    token = result.stdout.strip()
    return token or None


def save_keychain_token(token):
    if not keychain_available():
        raise SystemExit(
            "macOS Keychain недоступен. Используйте переменную окружения "
            f"{TOKEN_ENV_NAME}."
        )

    result = subprocess.run(
        [
            "security",
            "add-generic-password",
            "-U",
            "-a",
            KEYCHAIN_ACCOUNT,
            "-s",
            KEYCHAIN_SERVICE,
            "-w",
            token,
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        raise SystemExit(
            "Не удалось сохранить токен в macOS Keychain:\n"
            f"{result.stderr.strip()}"
        )


def forget_keychain_token():
    if not keychain_available():
        raise SystemExit("macOS Keychain недоступен.")

    result = subprocess.run(
        [
            "security",
            "delete-generic-password",
            "-a",
            KEYCHAIN_ACCOUNT,
            "-s",
            KEYCHAIN_SERVICE,
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode == 0:
        print("Сохранённый токен удалён из macOS Keychain.")
        return

    if "could not be found" in result.stderr:
        print("Сохранённого токена в macOS Keychain нет.")
        return

    raise SystemExit(
        "Не удалось удалить токен из macOS Keychain:\n"
        f"{result.stderr.strip()}"
    )


def token_api_base(token):
    return f"https://api.telegram.org/bot{token}"


def verify_token(token):
    bot = telegram_call(
        token_api_base(token),
        "getMe",
    )

    if bot.get("username"):
        bot_label = f"@{bot['username']}"
    else:
        bot_label = bot.get("first_name") or str(bot["id"])

    return bot, bot_label


def store_new_token():
    token = getpass("Новый токен бота: ").strip()

    if not token:
        raise SystemExit("Токен не введён.")

    _, bot_label = verify_token(token)
    save_keychain_token(token)

    print(
        f"Токен бота {bot_label} проверен "
        "и сохранён в macOS Keychain."
    )


def resolve_token():
    env_token = os.environ.get(TOKEN_ENV_NAME, "").strip()

    if env_token:
        return env_token, TOKEN_ENV_NAME

    keychain_token = read_keychain_token()

    if keychain_token:
        return keychain_token, "macOS Keychain"

    token = getpass("Токен бота: ").strip()

    if not token:
        raise SystemExit("Токен не введён.")

    if keychain_available():
        answer = input(
            "Сохранить токен в macOS Keychain для следующих запусков? "
            "[Y/n] "
        ).strip().lower()

        if answer in {"", "y", "yes", "д", "да"}:
            verify_token(token)
            save_keychain_token(token)
            return token, "введён и сохранён в macOS Keychain"

    return token, "введён вручную"


def read_post_file(post_path):
    """Прочитать Markdown-файл и проверить ограничения Rich Message."""

    post_path = post_path.expanduser()

    if not post_path.is_file():
        raise SystemExit(f"Файл не найден: {post_path}")

    try:
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


def print_preview(mode, post_path, post, char_count, notify):
    if mode == "test":
        target = f"тест: «{TEST_CHAT_LABEL}», chat_id={TEST_CHAT_ID}"
    else:
        target = f"финал: {FINAL_CHAT}"

    print()
    print(f"Режим: {target}")
    print(f"Уведомление: {'да' if notify else 'нет'}")
    print(f"Файл: {post_path}")
    print(f"Размер: {char_count} символов")
    print("\n----- НАЧАЛО ПОСТА -----\n")
    print(post)
    print("\n----- КОНЕЦ ПОСТА -----\n")


def validate_final_target(api_base, bot):
    """Проверить, что финальный получатель — именно @NeutrinoHit."""

    chat = telegram_call(
        api_base,
        "getChat",
        {"chat_id": FINAL_CHAT},
    )

    actual_id = chat.get("id")
    actual_type = chat.get("type")
    actual_title = chat.get("title", "")
    actual_username = chat.get("username", "")

    if actual_type != "channel":
        raise SystemExit(
            f"Остановка: {FINAL_CHAT} относится к типу "
            f"«{actual_type}», а не к каналу."
        )

    if actual_username.casefold() != FINAL_USERNAME.casefold():
        raise SystemExit(
            f"Остановка: Telegram вернул @{actual_username}, "
            f"а ожидался {FINAL_CHAT}."
        )

    membership = telegram_call(
        api_base,
        "getChatMember",
        {
            "chat_id": actual_id,
            "user_id": bot["id"],
        },
    )

    status = membership.get("status")

    if status not in {"administrator", "creator"}:
        raise SystemExit(
            f"Остановка: бот не является администратором {FINAL_CHAT}; "
            f"статус — {status!r}."
        )

    if (
        status == "administrator"
        and membership.get("can_post_messages") is not True
    ):
        raise SystemExit(
            f"Остановка: у бота нет права публиковать в {FINAL_CHAT}."
        )

    print(
        f"Финальный канал проверен: «{actual_title}» "
        f"(@{actual_username}), chat_id={actual_id}"
    )

    return actual_id


def confirm_final_publication():
    answer = input(
        f"Опубликовать этот пост в {FINAL_CHAT}? [y/N] "
    ).strip().lower()

    if answer not in {"y", "yes", "д", "да"}:
        raise SystemExit("Публикация отменена. Ничего не отправлено.")


def send_rich_message(api_base, chat_id, post, notify):
    return telegram_call(
        api_base,
        "sendRichMessage",
        {
            "chat_id": chat_id,
            "rich_message": {
                "markdown": post,
            },
            "disable_notification": not notify,
        },
    )


def main():
    args = parse_args()

    if args.forget_token:
        forget_keychain_token()
        return

    if args.store_token:
        store_new_token()
        return

    post_path, post, char_count = read_post_file(args.post)
    print_preview(
        args.mode,
        post_path,
        post,
        char_count,
        args.notify,
    )

    if args.dry_run:
        print("Dry run завершён: Telegram API не вызывался.")
        return

    token, token_source = resolve_token()
    api_base = token_api_base(token)

    if args.mode == "test":
        chat_id = TEST_CHAT_ID
        bot_label = None
    else:
        bot, bot_label = verify_token(token)
        chat_id = validate_final_target(api_base, bot)

        if not args.yes:
            confirm_final_publication()

    message = send_rich_message(
        api_base,
        chat_id,
        post,
        args.notify,
    )

    returned_chat = message.get("chat", {})
    returned_chat_id = returned_chat.get("id")

    if returned_chat_id != chat_id:
        raise SystemExit(
            "Telegram сообщил об успешной отправке, "
            f"но вернул неожиданный chat_id: {returned_chat_id}."
        )

    if args.mode == "test":
        channel_label = TEST_CHAT_LABEL
    else:
        channel_label = (
            returned_chat.get("title")
            or FINAL_CHAT
        )

    if bot_label:
        print(f"Бот: {bot_label}")

    print(f"Токен: {token_source}")
    print(
        f"Опубликовано в «{channel_label}». "
        f"message_id={message['message_id']}"
    )


if __name__ == "__main__":
    main()
