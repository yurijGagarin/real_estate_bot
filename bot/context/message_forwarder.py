import asyncio
import datetime
import logging
from typing import List, Optional

import pyrogram.errors.exceptions.all
from pyrogram import Client
from pyrogram.errors import FloodWait
from telegram.ext import ContextTypes

from bot.db import get_admin_users, save_user, get_user
from bot.exceptions import MessageNotFound

logger = logging.getLogger(__name__)


class MessageForwarder:
    app: Client
    from_chat_id: int
    wait_for: Optional[datetime.datetime] = None

    def __init__(self, app: Client, from_chat_id: int):
        self.app = app
        self.from_chat_id = from_chat_id

    @staticmethod
    def get_message_id_from_link(link):
        return int(link.split("/")[-1].split("\n")[0].split("?")[0])

    async def forward_message(self, message_link: str, chat_id: int):
        message_id = MessageForwarder.get_message_id_from_link(message_link)
        #todo:rewrite
        messages = await self.app.get_messages(
            chat_id=self.from_chat_id, message_ids=[message_id]
        )

        if len(messages) == 0:
            raise MessageNotFound(message_link=message_link)

        message = messages[0]
        message_ids = [message.id]
        if message.media_group_id is not None:
            #TODO: try to cache it
            media_group = await self.app.get_media_group(
                chat_id=self.from_chat_id, message_id=message_id
            )
            message_ids += [m.id for m in media_group]

        await self.app.forward_messages(
            chat_id=chat_id,
            from_chat_id=self.from_chat_id,
            message_ids=list(set(message_ids)),
        )

    async def forward_estates_to_user(self, user_id: int, message_links: List[str]):
        logger.info("Forward messages %s to user %s", message_links, user_id)
        user = await get_user(user_id)

        for message_link in message_links:
            try:
                if self.wait_for and self.wait_for >= datetime.datetime.now():
                    await self.app.send_message(chat_id=user.id, text=message_link)
                else:
                    await self.forward_message(message_link=message_link, chat_id=user.id)
                    self.wait_for = None
                await asyncio.sleep(1)
            except FloodWait as e:
                await self.app.send_message(chat_id=user.id, text=message_link)
                self.wait_for = datetime.datetime.now() + datetime.timedelta(seconds=e.value)
            except pyrogram.errors.exceptions.MessageIdInvalid:
                raise MessageNotFound(message_link=message_link)
            except pyrogram.errors.exceptions.bad_request_400.UserIsBlocked:

                error_text = (
                    f"Користувач з id: {user.id} припинив роботу бота.\nВідправка повідомлення до нього "
                    f"неможлива. Статус підписки змінено."
                )
                user.subscription = None
                user.subscription_text = (
                    f"З поверненням,{user.nickname}, ради Вас бачити знову."
                )
                await save_user(user)
                admin_users = await get_admin_users()
                for admin in admin_users:
                    await self.app.send_message(chat_id=admin.id, text=error_text)
                break


async def forward_static_content(chat_id: int,
                                 from_chat_id: int,
                                 message_id: int,
                                 context: ContextTypes.DEFAULT_TYPE):
    await context.bot.forwardMessage(
        chat_id=chat_id,
        from_chat_id=from_chat_id,
        message_id=message_id,
    )
