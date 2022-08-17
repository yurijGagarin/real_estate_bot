from typing import List

from pyrogram import Client


class MessageForwarder:
    app: Client
    from_chat_id: int

    def __init__(self, app: Client, from_chat_id: int):
        self.app = app
        self.from_chat_id = from_chat_id

    async def forward_messages(self, message_ids: List[int], chat_id: int):
        for message_id in message_ids:
            await self.forward_message(message_id=message_id, chat_id=chat_id)

    async def forward_message(self, message_id: int, chat_id: int):
        media_group = await self.app.get_media_group(chat_id=self.from_chat_id, message_id=message_id)
        await self.app.forward_messages(
            chat_id=chat_id,
            from_chat_id=self.from_chat_id,
            message_ids=[m.message_id for m in media_group],
        )