from typing import List

import telegram
from telegram._bot import BT

# from bot.ads.config import ADMINS_IDS


async def notify_admins(bot: BT, text: str):
    admin_users = ''.split('/') #TODO: fetch admin fromDB
    await notify_users(bot, text, admin_users)


async def notify_users(bot: BT, text: str, users: List):
    try:
        for user in users:
            await bot.send_message(chat_id=int(user), text=text)
    except (telegram.error.Forbidden, telegram.error.BadRequest):
        ...
