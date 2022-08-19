from typing import List

from pyrogram import Client


class MessageForwarder:
    app: Client
    from_chat_id: int

    def __init__(self, app: Client, from_chat_id: int):
        self.app = app
        self.from_chat_id = from_chat_id

    def get_message_id_from_link(self, link):
        return int(link.split('/')[-1].split('\n')[0].split('?')[0])

    async def forward_messages(self, message_ids: List[int], chat_id: int):
        for message_id in message_ids:
            await self.forward_message(message_id=message_id, chat_id=chat_id)

    async def forward_message(self, message_id: int, chat_id: int):
        messages = await self.app.get_messages(chat_id=self.from_chat_id, message_ids=[message_id])

        if len(messages) == 0:
            return

        message = messages[0]
        message_ids = [message.message_id]
        if message.media_group_id is not None:
            media_group = await self.app.get_media_group(chat_id=self.from_chat_id, message_id=message_id)
            message_ids += [m.message_id for m in media_group]

        await self.app.forward_messages(
            chat_id=chat_id,
            from_chat_id=self.from_chat_id,
            message_ids=list(set(message_ids)),
        )

    async def forward_estates_to_user(self, user_id: int, links: List[str]):
        message_ids = [self.get_message_id_from_link(link) for link in links]
        await self.forward_messages(
            message_ids=message_ids,
            chat_id=user_id,
        )
