import json
from json import JSONDecodeError
from typing import Type, List

from sqlalchemy.sql import Select
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Update
from telegram.ext import ContextTypes

from bot.context.filters import BaseFilter
from bot.context.payload import Payload
from bot.context.state import State
from bot.db import get_result
from bot.models import Ad
from bot.navigation import main_menu_buttons, ACTION_NEXT, ACTION_BACK, MAIN_MENU, MAIN_MENU_TEXT, LOAD_MORE_LINKS_TEXT, \
    MAIN_MENU_BTN_TEXT, LOAD_MORE_LINKS_BTN_TEXT


class Manager:
    filters: List[BaseFilter]
    query: Select
    context: ContextTypes.DEFAULT_TYPE
    update: Update

    def __init__(self,
                 model: Type[Ad],
                 filters: List[Type[BaseFilter]],
                 update: Update,
                 context: ContextTypes.DEFAULT_TYPE
                 ):
        self.update = update
        self.context = context
        self.state = State.from_context(context)
        self.filters = []

        prev_filter = None
        for i in range(len(filters)):
            f = filters[i]
            if i >= len(self.state.filters):
                self.state.filters.append(None)
            s = self.state.filters[i]
            filter_obj = f(state=s, prev_filter=prev_filter, model=model)
            prev_filter = filter_obj
            self.filters.append(filter_obj)

    @property
    def active_filter(self):
        return self.filters[self.state.filter_index]

    async def process_action(self):
        payload = self.get_payload()

        if ACTION_NEXT in payload.callback:
            if self.state.filter_index < len(self.filters) - 1:
                self.move_forward()
            else:
                return await self.show_result()

        elif ACTION_BACK in payload.callback:
            self.state.filters[self.state.filter_index] = None
            self.move_back()

        elif 'else' in payload.callback:
            return await self.show_result()
        elif MAIN_MENU in payload.callback:
            reply_markup = await main_menu_buttons()
            await self.reset_state()
            return await self.update.callback_query.edit_message_text(text=MAIN_MENU_TEXT,
                                                                      reply_markup=reply_markup
                                                                      )
        else:
            self.state.result_sliced_view = 0
            self.state.filters[self.state.filter_index] = await self.active_filter.process_action(payload, self.update)

        await self.edit_message()
        self.save_state()

    async def reset_state(self):
        self.state.filters = []
        self.state.filter_index = 0
        self.save_state()

    def move_forward(self):
        self.state.filter_index += 1

    def move_back(self):
        self.state.filter_index -= 1

    async def edit_message(self):
        kbrd = await self.active_filter.build_keyboard()
        if self.state.filter_index > 0:
            kbrd.append([InlineKeyboardButton('Назад', callback_data='{"b":1}')])

        if self.active_filter.allow_next():
            kbrd.append([InlineKeyboardButton('Далі', callback_data='{"n":1}')])

        text = ['Обрані фільтри:']
        for i in range(self.state.filter_index + 1):
            f = self.filters[i]
            text.append(f.build_text())
        keyboard = InlineKeyboardMarkup(kbrd)
        callback_query = self.update.callback_query
        if callback_query is None:
            callback_query = self.context.user_data['callback_query']

        await callback_query.edit_message_text(text='\n'.join(text), reply_markup=keyboard)

        self.context.user_data['callback_query'] = callback_query

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
        q = await self.active_filter.get_query()
        result = await get_result(q)
        if len(result) > 10:
            sliced_result = result[self.state.result_sliced_view: (self.state.result_sliced_view + 10)]
            self.state.result_sliced_view += 10
            self.save_state()

            reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton(LOAD_MORE_LINKS_TEXT,
                                                                       callback_data='{"else": 1}')],
                                                 [InlineKeyboardButton(MAIN_MENU_BTN_TEXT,
                                                                       callback_data='{"%s": 1}' % MAIN_MENU)]
                                                 ])

            for link in sliced_result:
                await self.context.bot.send_message(chat_id=self.update.effective_chat.id, text=link)
            await self.context.bot.send_message(chat_id=self.update.effective_chat.id,
                                                text=LOAD_MORE_LINKS_BTN_TEXT,
                                                reply_markup=reply_markup)
        else:
            for link in result:
                await self.context.bot.send_message(chat_id=self.update.effective_chat.id, text=link)

    def save_state(self):
        self.state.update_context(self.context)
