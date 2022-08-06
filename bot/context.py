import json
from json import JSONDecodeError
from typing import Type, List

from sqlalchemy.sql import Select
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Update
from telegram.ext import ContextTypes

from bot.db import get_result
from bot.filters import BaseFilter
from bot.navigation import main_menu_buttons
from bot.models import Ad


class State:
    def __init__(self, filter_index, filters):
        self.filter_index = filter_index
        self.filters = filters

    def to_json(self):
        return json.dumps({
            'i': self.filter_index,
            'f': self.filters,
        })

    @classmethod
    def from_json(cls, raw_data):
        data = json.loads(raw_data)

        return cls(
            filter_index=data.get('i') or 0,
            filters=data.get('f') or []
        )

    @classmethod
    def from_context(cls, context: ContextTypes.DEFAULT_TYPE):
        return cls.from_json(context.user_data.get('filter_state') or '{}')


ACTION_NEXT = 'n'
ACTION_BACK = 'b'
MAIN_MENU = 'm'


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

    # TODO: make more readable code --> declarative one ( what is doing and not how  its  doing)
    async def process_action(self):
        payload = self.get_payload()

        if payload is not None:
            if ACTION_NEXT in payload:
                if self.state.filter_index < len(self.filters) - 1:
                    self.state.filter_index += 1
                else:
                    return await self.show_result()
            elif ACTION_BACK in payload:
                self.state.filters[self.state.filter_index] = None
                self.state.filter_index -= 1
            elif 'else' in payload:
                return await self.show_result()
            elif MAIN_MENU in payload:
                reply_markup = await main_menu_buttons()
                # TODO FIX STATE RESET
                self.state.filters = []
                self.state.filter_index = 0
                self.save_state()
                return await self.update.callback_query.edit_message_text(text='Головне меню', reply_markup=reply_markup)
            else:
                self.context.user_data['result_sliced_view'] = 0
                self.state.filters[self.state.filter_index] = await self.active_filter.process_action(payload)

        await self.edit_message()
        self.save_state()

    async def edit_message(self):
        kbrd = await self.active_filter.build_keyboard()
        if self.state.filter_index > 0:
            kbrd.append([InlineKeyboardButton('Back', callback_data='{"b":1}')])

        if self.active_filter.allow_next():
            kbrd.append([InlineKeyboardButton('Next', callback_data='{"n":1}')])

        text = ['Твої фільтри:']
        for i in range(self.state.filter_index + 1):
            f = self.filters[i]
            text.append(f.build_text())
        keyboard = InlineKeyboardMarkup(kbrd, resize_keyboard=False)
        await self.update.callback_query.edit_message_text(text='\n'.join(text), reply_markup=keyboard)

    def get_payload(self):
        try:
            return json.loads(self.update.callback_query.data)
        except JSONDecodeError as e:
            return None

    async def show_result(self):
        q = await self.active_filter.get_query()
        result = await get_result(q)
        if len(result) > 10:
            sliced_result = result[
                            self.context.user_data['result_sliced_view']
                            :
                            (10 + self.context.user_data['result_sliced_view'])
                            ]
            self.context.user_data['result_sliced_view'] += 10
            reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("Ще огологощення",
                                                                       callback_data='{"else": 1}')],
                                                 [InlineKeyboardButton("Головне Меню",
                                                                       callback_data='{"m": 1}')]
                                                 ])
            for link in sliced_result:
                await self.context.bot.send_message(chat_id=self.update.effective_chat.id, text=link)
            await self.context.bot.send_message(chat_id=self.update.effective_chat.id,
                                                text="Ще варіанти",
                                                reply_markup=reply_markup)
        else:
            for link in result:
                await self.context.bot.send_message(chat_id=self.update.effective_chat.id, text=link)

    def save_state(self):
        self.context.user_data['filter_state'] = self.state.to_json()
