from typing import List

import telegram
from telegram._bot import BT

from bot.db import get_admin_users
from bot.models import User


async def notify_admins(bot: BT, text: str):
    admin_users = await get_admin_users()
    await notify_users(bot, text, admin_users)


async def notify_users(bot: BT, text: str, users: List[User]):
    for user in users:
        await bot.send_message(chat_id=user.id, text=text, parse_mode="HTML")


async def send_message_to_users(bot: BT, users: List[User], text: str):
    blocked_users = []
    for user in users:
        try:
            await bot.send_message(
                chat_id=user.id,
                text=text,
                parse_mode="HTML"
            )
        except telegram.error.Forbidden:
            error_text = (
                f"Користувач з id: {user.id} припинив роботу бота.\nВідправка повідомлення до нього "
                f"неможлива. Статус підписки змінено."
            )
            blocked_users.append(user)
            admin_users = await get_admin_users()
            for admin in admin_users:
                await bot.send_message(chat_id=admin.id, text=error_text, parse_mode="HTML")

    return blocked_users
