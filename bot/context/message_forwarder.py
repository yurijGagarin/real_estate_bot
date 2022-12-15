import asyncio
import datetime
import logging
from typing import List, Optional, Dict

import pyrogram.errors.exceptions.all
from pyrogram import Client
from pyrogram.errors import FloodWait
from pyrogram.types import InputMediaPhoto, InputMediaVideo
from telegram.ext import ContextTypes

import bot.models
from bot.db import get_admin_users, save_user, get_user, get_model_by_link
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
        message_id = self.get_message_id_from_link(message_link)
        messages = await self.app.get_messages(
            chat_id=self.from_chat_id, message_ids=[message_id]
        )

        if len(messages) == 0:
            raise MessageNotFound(message_link=message_link)

        message = messages[0]
        if message.media_group_id is not None:
            parsing_result = await self.parse_media_group(message_id, message_link)
            try:
                await self.app.send_media_group(chat_id=chat_id, media=parsing_result['media_group_to_send'])
            except pyrogram.errors.exceptions.bad_request_400.InputUserDeactivated as e:
                print(e)
        else:
            pass
            # await self.app.send_message(chat_id=chat_id, text=message_link)

    async def parse_media_group(self, message_id, message_link) -> Dict:
        model = await get_model_by_link(bot.models.Apartments, message_link) \
                or await get_model_by_link(bot.models.Houses, message_link)
        strings_to_remove_in_caption = ['🔍 @real_estate_rent_bot Бот для пошуку',
                                        '🏚 @LvivNovobud канал з продажу',
                                        '🔍 @real_estate_rent_bot бот для пошуку']
        parsed_media_group = await self.app.get_media_group(
            chat_id=self.from_chat_id, message_id=message_id)
        result = {'media_group_to_send': []}
        original_caption = ''
        for m in parsed_media_group:
            media = None
            if m.photo:
                media = InputMediaPhoto(m.photo.file_id, caption=m.caption)
            elif m.video:
                media = InputMediaVideo(m.video.file_id, caption=m.caption)
            if media is None:
                continue
            if not original_caption and m.caption:
                original_caption = m.caption
            result['media_group_to_send'].append(media)
        lined_caption = original_caption.split('\n')
        new_caption = []
        manager_username = None
        manager_phone_number = None
        for line in lined_caption:
            if '📩' in line:
                manager_username = line
                continue
            if '☎️' in line:
                manager_phone_number = line.split()[1]
                continue
            if line in strings_to_remove_in_caption:
                continue
            new_caption.append(line)
        if manager_phone_number is not None:
            new_caption += [f'<a href="tel:{manager_phone_number}">☎️ {manager_phone_number} ⬅️ зателефонувати</a>']
        if manager_username is not None:
            new_caption += [f'{manager_username} ⬅️ записатися на перегляд',
                            '', ]
        if model.maps_link is not None:
            new_caption += [f"🗺 <a href='{model.maps_link}'>Розташування ЖК на Google maps</a>"]
        new_caption += [f"🔍 <a href='{message_link}'>Посилання на об'єкт в каналі</a>",
                        '',
                        '🏚 @LvivOG канал з орендою',
                        '🏚 @LvivNovobud канал з продажу']
        result['media_group_to_send'][0].caption = '\n'.join(new_caption)
        return result

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
