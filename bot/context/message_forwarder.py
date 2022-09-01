import logging
from typing import List

import pyrogram.errors.exceptions.all
from pyrogram import Client

from bot.exceptions import MessageNotFound

logger = logging.getLogger(__name__)


class MessageForwarder:
    app: Client
    from_chat_id: int

    def __init__(self, app: Client, from_chat_id: int):
        self.app = app
        self.from_chat_id = from_chat_id

    @staticmethod
    def get_message_id_from_link(link):
        return int(link.split('/')[-1].split('\n')[0].split('?')[0])

    async def forward_message(self, message_link: str, chat_id: int):
        message_id = MessageForwarder.get_message_id_from_link(message_link)
        messages = await self.app.get_messages(chat_id=self.from_chat_id, message_ids=[message_id])

        if len(messages) == 0:
            raise MessageNotFound(message_link=message_link)

        message = messages[0]
        message_ids = [message.id]
        if message.media_group_id is not None:
            media_group = await self.app.get_media_group(chat_id=self.from_chat_id, message_id=message_id)
            message_ids += [m.id for m in media_group]

        await self.app.forward_messages(
            chat_id=chat_id,
            from_chat_id=self.from_chat_id,
            message_ids=list(set(message_ids)),
        )

    async def forward_estates_to_user(self, user_id: int, message_links: List[str]):
        logger.info('Forward messages %s to user %s', message_links, user_id)

        for message_link in message_links:
            try:
                await self.forward_message(message_link=message_link, chat_id=user_id)
            except pyrogram.errors.exceptions.MessageIdInvalid as e:
                print(e)
                raise MessageNotFound(message_link=message_link)
            except pyrogram.errors.exceptions.bad_request_400.UserIsBlocked as blocked:
                print(blocked)
