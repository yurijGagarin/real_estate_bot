import json
from collections import defaultdict
from typing import Dict, List, Optional, Type

from sqlalchemy import or_, and_, Column
from sqlalchemy import select
from sqlalchemy.sql import Select
from telegram import InlineKeyboardButton, Update

from bot.api.monobank_currency import get_exchange_rates
from bot.context.payload import Payload
from bot.db import get_unique_el_from_db
from bot.log import logging
from bot.models import Ad, Apartments, Houses


def function_logger(func):
    async def wrapper(*args, **kwargs):
        q = await func(*args, **kwargs)
        logging.info(q)
        return q

    return wrapper


class BaseFilter:
    __query: Optional[Select]
    name: str
    select_all_text = 'Обрати всі'
    unselect_all_text = 'Зняти виділення з усіх'
    has_select_all: bool
    desired_amount_of_rows: int = 2
    skip_filters_text = 'Без різниці'
    has_skip_filter: bool

    def __init__(self,
                 model: Type[Ad],
                 state: Optional[Dict],
                 prev_filter: Optional['BaseFilter'] = None,
                 name: Optional[str] = None):

        if name:
            self.name = name
        self.model = model
        self.prev_filter = prev_filter
        self.state = state or {
            SELECTED_VALUES: defaultdict(bool, {}),  # Selected values
            SELECT_ALL: None,  # Select all
            PAGE_IDX: 0,  # Current page
        }
        self.__query = None

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

    async def build_items_keyboard(self):
        items = await self.get_items()
        # if len(items) > 20:
        #     keyboard = await self.paginator(items)
        #     return keyboard
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
        if len(row):
            keyboard.append(row)
        return keyboard

    async def build_keyboard(self) -> List[List[InlineKeyboardButton]]:
        """Helper function to build the next inline keyboard."""
        keyboard = await self.build_items_keyboard()

        if self.has_select_all:
            if self.select_all:
                keyboard.append([InlineKeyboardButton(self.unselect_all_text, callback_data='{"%s": 0}' % SELECT_ALL)])
            else:
                keyboard.append([InlineKeyboardButton(self.select_all_text, callback_data='{"%s": 1}' % SELECT_ALL)])
        if self.has_skip_filter:
            keyboard.append([InlineKeyboardButton(self.skip_filters_text, callback_data='{"a": 1}')])
        return keyboard

    #
    async def process_action(self, payload: Payload, update: Update):
        print(payload)
        items = await self.get_items()
        if SELECT_ALL in payload.callback:
            self.select_all = payload.callback[SELECT_ALL]
            for key in items:
                self.selected_values[key] = payload.callback[SELECT_ALL]
        elif SELECTED_VALUES in payload.callback:
            key = items[payload.callback[SELECTED_VALUES]]
            self.selected_values[key] = not self.state.get(key)
        elif PAGE_IDX in payload.callback:
            self.page_idx = payload.callback[PAGE_IDX]

        return dict(self.state)

    def allow_next(self):
        return len(list(filter(None, self.state.values())))

    async def build_text(self):
        items = await self.get_items()
        return f'{self.name}: ' + ', '.join([k for k in items if self.state[k]])

    async def get_items(self):
        return []


class ColumnFilter(BaseFilter):

    def get_column(self) -> Column:
        raise NotImplementedError()

    async def get_items(self):
        data = await get_unique_el_from_db(await self.get_query(), self.get_column())
        return data

    @function_logger
    async def build_query(self):
        data = await self.get_items()

        filtered_data = []

        for datum in data:
            if self.state[str(datum)]:
                filtered_data.append(datum)

        query = await self.get_query()
        if len(filtered_data):
            return query.filter(self.get_column().in_(filtered_data))
        return query.filter()


class DistrictFilter(ColumnFilter):
    name = 'Райони'
    has_select_all = True
    has_skip_filter = True

    def get_column(self) -> Column:
        return self.model.district


class ResidentialComplexFilter(ColumnFilter):
    name = 'ЖК'
    has_select_all = True
    has_skip_filter = True

    model: Type[Apartments]

    def get_column(self) -> Column:
        return self.model.residential_complex


class RoomsFilter(BaseFilter):
    name = 'Кількість кімнат'

    max_rooms = 4
    has_select_all = False
    has_skip_filter = True

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
        return await get_unique_el_from_db(await self.get_query(), self.model.rooms)

    @function_logger
    async def build_query(self):
        rooms_qty = await self.get_rooms_qty()
        items = []
        for r_qty in range(1, self.max_rooms):
            if self.state[str(r_qty)]:
                items.append(r_qty)
            try:
                rooms_qty.remove(r_qty)
            except ValueError:
                pass

        if self.state[f'{self.max_rooms}+']:
            items += rooms_qty

        query = await self.get_query()
        if len(items):
            return query.filter(self.model.rooms.in_(items))
        return query.filter()


class PriceFilter(BaseFilter):
    name = 'Ціна'
    has_select_all = False
    has_skip_filter = True

    async def build_text(self):
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

    @function_logger
    async def build_query(self):
        q = await self.get_query()
        price_from = self.state['price_from']
        price_to = self.state['price_to']

        currencies = get_exchange_rates()

        filters = []
        for k, v in currencies.items():
            f = and_(self.model.currency == k, price_from / v <= self.model.rent_price,
                     self.model.rent_price <= price_to / v)
            filters.append(f)

        q = q.filter(or_(*filters))

        return q


class LivingAreaFilter(BaseFilter):
    name = 'Площа'
    has_select_all = False
    model: Type[Houses]

    async def get_items(self):
        living_areas = ['< 100м2', '100-200м2', '200-300м2', '> 300м2']
        return living_areas

    @function_logger
    async def build_query(self):
        q = await self.get_query()
        # TODO rewrite better
        living_areas = {
            '< 100м2': [0, 100],
            '100-200м2': [100, 200],
            '200-300м2': [200, 300],
            '> 300м2': [300, 10000],

        }
        area_from = []
        area_to = []
        for k, v in living_areas.items():
            if self.state[k]:
                area_from.append(v[0])
                area_to.append(v[1])

        area_from_v = min(area_from)
        area_to_v = max(area_to)

        stmt = and_(area_from_v <= self.model.living_area, self.model.living_area <= area_to_v)
        q = q.filter(stmt)
        return q
