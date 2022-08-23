import datetime
import json
from json import JSONDecodeError
from typing import Type, List

from sqlalchemy.ext.serializer import dumps
from sqlalchemy.sql import Select
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Update, Message
from telegram.ext import ContextTypes

from bot.context.filters import BaseFilter
from bot.context.message_forwarder import MessageForwarder
from bot.context.payload import Payload
from bot.context.state import State
from bot.db import get_result, get_user, save_user, delete_model_by_link, get_model_by_link
from bot.exceptions import MessageNotFound
from bot.models import Ad
from bot.navigation import ACTION_NEXT, ACTION_BACK, MAIN_MENU, LOAD_MORE_LINKS_BTN_TEXT, SUBSCRIPTION_MODE, \
    SHOW_NEXT_PAGE, BACK_BTN, SHOW_ITEMS_PER_PAGE, \
    NEXT_PAGE_BTN, MAIN_MENU_BTN, SUBSCRIPTION_BTN, EMPTY_RESULT_TEXT, THATS_ALL_FOLKS_TEXT, show_subscription_menu
from bot.notifications import notify_admins


class Manager:
    filters: List[BaseFilter]
    query: Select
    context: ContextTypes.DEFAULT_TYPE
    update: Update
    model: Type[Ad]

    def __init__(self, model: Type[Ad], filters: List[Type[BaseFilter]], update: Update,
                 context: ContextTypes.DEFAULT_TYPE, forwarder: MessageForwarder):
        self.update = update
        self.context = context
        self.state = State.from_context(context)
        self.filters = []
        self.forwarder = forwarder
        self.model = model

        prev_filter = None
        for i in range(len(filters)):
            f = filters[i]
            if i >= len(self.state.filters):
                self.state.filters.append(None)
            s = self.state.filters[i]
            filter_obj = f(state=s, prev_filter=prev_filter, model=model)
            prev_filter = filter_obj
            self.filters.append(filter_obj)

    def get_state(self):
        return self.state

    @property
    def active_filter(self):
        return self.filters[self.state.filter_index]

    @property
    def is_subscription(self):
        return self.state.is_subscription

    async def process_action(self):
        payload = self.get_payload()

        if ACTION_NEXT in payload.callback:
            if self.state.filter_index < len(self.filters) - 1:
                self.move_forward()
            else:
                if self.is_subscription:
                    await self.create_subscription()

                    return False
                await self.show_result()
                return True

        elif ACTION_BACK in payload.callback:
            if self.state.filter_index == 0:
                return False
            self.state.filters[self.state.filter_index] = None
            self.move_back()
        elif SHOW_NEXT_PAGE in payload.callback:
            await self.show_result()
            return True
        elif MAIN_MENU in payload.callback:
            await self.reset_state()
            return False
        elif SUBSCRIPTION_MODE in payload.callback:
            await self.create_subscription()
            await show_subscription_menu(self.update)
            return False
        else:
            self.state.filters[self.state.filter_index] = await self.active_filter.process_action(payload, self.update)

        await self.edit_message()
        self.save_state()
        return True

    async def reset_state(self):
        self.state.result_sliced_view = None
        self.state.filters = []
        self.state.filter_index = 0
        self.save_state()

    def move_forward(self):
        self.state.filter_index += 1

    def move_back(self):
        last_filter = len(self.state.filters) - 1
        if self.state.filter_index == last_filter and self.state.result_sliced_view is not None:
            self.state.result_sliced_view = None
            return
        self.state.filter_index -= 1

    async def edit_message(self):
        kbrd = await self.active_filter.build_keyboard()
        navigation_row = []
        if self.state.filter_index >= 0:
            navigation_row.append(BACK_BTN)

        if self.active_filter.allow_next():
            next_text = 'Пропустити ➡'
            if self.active_filter.has_values():
                next_text = '➡️'
            navigation_row.append(await self.NEXT_BTN(next_text))
        kbrd.append(navigation_row)

        text = ['Обрані фільтри:']
        for i in range(self.state.filter_index + 1):
            f = self.filters[i]
            text.append(await f.build_text())
        text = list(filter(None, text))
        keyboard = InlineKeyboardMarkup(kbrd)
        callback_query = self.update.callback_query
        if callback_query is None:
            callback_query = self.context.user_data['callback_query']

        new_text = '\n'.join(text)

        # Edit message only if it has diff
        if not self.context.user_data.get('callback_query') or \
                new_text != callback_query.message.text or \
                keyboard.inline_keyboard != callback_query.message.reply_markup.inline_keyboard:
            edit_result = await callback_query.edit_message_text(text=new_text, reply_markup=keyboard)

            if isinstance(edit_result, Message):
                callback_query.message = edit_result
            self.context.user_data['callback_query'] = callback_query

    async def NEXT_BTN(self, next_text):
        return InlineKeyboardButton(next_text, callback_data='{"n":1}')


    def get_payload(self):
        message = ""
        callback = {}
        try:
            callback = json.loads(self.update.callback_query.data)
        except (JSONDecodeError, AttributeError):
            ...

        try:
            message = self.update.message.text
        except (JSONDecodeError, AttributeError):
            ...

        return Payload(message=message, callback=callback)

    async def show_result(self):
        while True:
            try:
                await self._show_result()
                break
            except MessageNotFound as e:
                print(e.message_link)
                await self.notify_admins_about_bad_link(e.message_link)
                await delete_model_by_link(self.model, e.message_link)

    async def _show_result(self):
        q = await self.active_filter.build_query()
        all_items_result = await get_result(q, self.model)
        all_items_result_len = len(all_items_result)
        has_pagination = all_items_result_len > SHOW_ITEMS_PER_PAGE
        empty_result = not all_items_result_len
        keyboard = []
        page_offset = self.state.result_sliced_view or 0
        items_result = all_items_result[
                       page_offset: (page_offset + SHOW_ITEMS_PER_PAGE)]
        last_page = len(items_result) < SHOW_ITEMS_PER_PAGE
        text = ''
        if has_pagination and not last_page:
            page_offset += SHOW_ITEMS_PER_PAGE
            text = LOAD_MORE_LINKS_BTN_TEXT
            keyboard.append(NEXT_PAGE_BTN)

        keyboard.append([BACK_BTN, MAIN_MENU_BTN])
        keyboard.append([SUBSCRIPTION_BTN])
        reply_markup = InlineKeyboardMarkup(keyboard)

        if empty_result:
            text = EMPTY_RESULT_TEXT
            return await self.update.callback_query.edit_message_text(text=text, reply_markup=reply_markup)
        if last_page:
            text = THATS_ALL_FOLKS_TEXT

        await self.forwarder.forward_estates_to_user(user_id=self.update.effective_user.id, message_links=items_result)
        await self.context.bot.send_message(chat_id=self.update.effective_chat.id,
                                            text=text,
                                            reply_markup=reply_markup)
        self.state.result_sliced_view = page_offset
        self.save_state()

    def save_state(self):
        self.state.update_context(self.context)

    async def create_subscription(self):
        user = await get_user(self.update)
        query = await self.active_filter.build_query()
        serialized = dumps(query)
        user.subscription = serialized
        text = ['Обрані фільтри:']
        for i in range(self.state.filter_index + 1):
            f = self.filters[i]
            text.append(await f.build_text(is_final=True))
        user.subscription_text = '\n'.join(text)
        user.last_viewed_at = datetime.datetime.utcnow()
        await save_user(user)
        await self.reset_state()

    async def notify_admins_about_bad_link(self, message_link: str):
        model = await get_model_by_link(self.model, message_link)
        text = f"Something wrong with: {model.get_full_name()}"

        await notify_admins(self.context.bot, text)
