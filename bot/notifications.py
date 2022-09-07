from typing import List

from telegram._bot import BT

from bot.db import get_admin_users
from bot.models import User


async def notify_admins(bot: BT, text: str):
    admin_users = await get_admin_users()
    await notify_users(bot, text, admin_users)


async def notify_users(bot: BT, text: str, users: List[User]):
    for user in users:
        await bot.send_message(chat_id=user.id, text=text)
