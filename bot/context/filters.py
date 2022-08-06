import json
from collections import defaultdict
from sqlalchemy import or_, and_
from typing import Dict, List, Optional, Type

from sqlalchemy import select
from sqlalchemy.sql import Select
from telegram import InlineKeyboardButton, Update

from bot.context.payload import Payload
from bot.db import get_unique_el_from_db
from bot.log import logging
from bot.models import Ad, Apartments


def function_logger(func):
    async def wrapper(*args, **kwargs):
        q = await func(*args, **kwargs)
        logging.info(q)
        return q

    return wrapper


class BaseFilter:
    __query: Optional[Select]
    name: str
    select_all = 'Обрати всі'
    unselect_all = 'Зняти виділення з усіх'
    has_select_all: bool
    desired_amount_of_rows: int

    def __init__(self,
                 model: Type[Ad],
                 state: Optional[Dict],
                 prev_filter: Optional['BaseFilter'] = None,
                 name: Optional[str] = None,
                 desired_amount_of_rows: Optional[int] = 2):
        if name:
            self.name = name
        self.model = model
        self.prev_filter = prev_filter
        self.state = defaultdict(bool, state or {})
        self.__query = None
        self.desired_amount_of_rows = desired_amount_of_rows

    @function_logger
    async def build_query(self):
        return (await self.get_query()).filter()

    async def get_query(self):
        if self.__query is None:
            if self.prev_filter is not None:
                self.__query = await self.prev_filter.build_query()
            else:
                self.__query = select(self.model)
        return self.__query

    async def button_builder(self):
        items = await self.get_items()
        keyboard = []
        row = []
        i = 0
        for item in items:
            item_value = item
            data = json.dumps({
                'v': i,
            })
            title = item_value
            if self.state.get(item_value):
                title = f'{title} ✅'
            row.append(InlineKeyboardButton(title, callback_data=data))
            if len(row) == self.desired_amount_of_rows:
                keyboard.append(row)
                row = []
            i += 1
        return keyboard

    async def build_keyboard(self) -> List[List[InlineKeyboardButton]]:
        """Helper function to build the next inline keyboard."""
        items = await self.get_items()
        if len(items) <= 2:
            self.desired_amount_of_rows = 1
            keyboard = await self.button_builder()

        elif len(items) <= 8:
            keyboard = await self.button_builder()

        else:
            self.desired_amount_of_rows = 3
            keyboard = await self.button_builder()

        if self.has_select_all:
            if self.state.get('s'):
                keyboard.append([InlineKeyboardButton(self.unselect_all, callback_data='{"s": 0}')])
            else:
                keyboard.append([InlineKeyboardButton(self.select_all, callback_data='{"s": 1}')])

        return keyboard

    #
    async def process_action(self, payload: Payload, update: Update):
        print(payload)
        items = await self.get_items()
        if 's' in payload.callback:
            self.state['s'] = payload.callback['s']
            for key in items:
                self.state[key] = payload.callback['s']
        elif 'v' in payload.callback:
            key = items[payload.callback['v']]
            self.state[key] = not self.state.get(key)
        return dict(self.state)

    def allow_next(self):
        return len(list(filter(None, self.state.values())))

    def build_text(self):
        items = self.state.items()
        return f'{self.name}: ' + ', '.join([k for k, v in items if v])

    async def get_items(self):
        return []


class RoomsBaseFilter(BaseFilter):
    name = 'Кількість кімнат'
    max_rooms = 4
    has_select_all = False

    def __init__(self,
                 model: Type[Ad],
                 state: Optional[Dict],
                 prev_filter: Optional['BaseFilter'] = None,
                 name: Optional[str] = None):
        super().__init__(model, state, prev_filter, name)

    async def get_items(self):
        rooms_qty = await self.get_rooms_qty()

        items = []
        for r_qty in range(1, self.max_rooms):
            if r_qty in rooms_qty:
                items.append(str(r_qty))
                rooms_qty.remove(r_qty)
        if len(rooms_qty):
            items.append(f'{self.max_rooms}+')

        return items

    async def get_rooms_qty(self) -> List[int]:
        return await get_unique_el_from_db(await self.get_query(), 'rooms')

    @function_logger
    async def build_query(self):
        rooms_qty = await self.get_rooms_qty()

        items = []
        for r_qty in range(1, self.max_rooms):
            if self.state[str(r_qty)]:
                items.append(r_qty)
            rooms_qty.remove(r_qty)

        if self.state[f'{self.max_rooms}+']:
            items += rooms_qty

        query = await self.get_query()
        if len(items):
            return query.filter(self.model.rooms.in_(items))
        return query.filter()


class DistrictBaseFilter(BaseFilter):
    name = 'Райони'
    has_select_all = True

    async def get_items(self):
        data = await get_unique_el_from_db(await self.get_query(), 'district')
        return data

    @function_logger
    async def build_query(self):
        legal_districts = await self.get_items()

        items = []

        for district in legal_districts:
            if self.state[str(district)]:
                items.append(district)

        query = await self.get_query()
        if len(items):
            return query.filter(self.model.district.in_(items))
        return query.filter()


class ResidentialComplexBaseFilter(BaseFilter):
    name = 'ЖК'
    has_select_all = True

    def __init__(self,
                 model: Type[Apartments],
                 state: Optional[Dict],
                 prev_filter: Optional['BaseFilter'] = None,
                 name: Optional[str] = None):
        super().__init__(model, state, prev_filter, name)

    async def get_items(self):
        data = await get_unique_el_from_db(await self.get_query(), 'residential_complex')

        return data

    @function_logger
    async def build_query(self):
        legal_res_complexes = await self.get_items()

        items = []

        for res_complex in legal_res_complexes:
            if self.state[str(res_complex)]:
                items.append(res_complex)
            legal_res_complexes.remove(res_complex)

        query = await self.get_query()
        if len(items):
            return query.filter(self.model.residential_complex.in_(items))
        return query.filter()


class PriceFilter(BaseFilter):
    name = 'Ціна'
    has_select_all = False

    async def get_items(self):
        return []

    def build_text(self):
        from_text = 'від ' + str(self.state['price_from'])
        to_text = 'до ' + str(self.state['price_to'])
        if not self.state['price_from']:
            return 'Введіть нижню межу ціни 👇'
        elif not self.state['price_to']:
            return f'{self.name}: ' + from_text + ' \nВведіть верхню межу ціни 👇'
        else:
            return f'{self.name}: ' + from_text + ' ' + to_text

    async def process_action(self, payload: Payload, update: Update):
        try:
            number = int(payload.message.strip())
            if not self.state['price_from']:
                self.state['price_from'] = number
            elif not self.state['price_to']:
                self.state['price_to'] = number
        except ValueError:
            pass

        if payload.message:
            await update.message.delete()

        return dict(self.state)

    def allow_next(self):
        return self.state['price_from'] and self.state['price_to']

    async def build_query(self):
        q = await self.get_query()
        price_from = self.state['price_from']
        price_to = self.state['price_to']
        currencies = {
            'USD': 30,
            'EUR': 32,
            'UAH': 1,
        }

        filters = []
        for k, v in currencies.items():
            f = and_(self.model.currency == k, price_from / v <= self.model.rent_price,
                     self.model.rent_price <= price_to / v)
            filters.append(f)

        q = q.filter(or_(*filters))

        return q
