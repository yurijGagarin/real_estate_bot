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


SELECTED_VALUES = 'v'
SELECT_ALL = 's'
PAGE_IDX = 'p'

ITEMS_PER_PAGE = 20


class BaseFilter:
    __query: Optional[Select]
    name: str
    select_all_text = 'Обрати всі ✅'
    unselect_all_text = 'Зняти виділення з усіх ❌'
    has_select_all: bool
    desired_amount_of_rows: int = 2

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
            SELECTED_VALUES: {},  # Selected values
            SELECT_ALL: None,  # Select all
            PAGE_IDX: 0,  # Current page
        }
        self.state[SELECTED_VALUES] = defaultdict(bool, self.state[SELECTED_VALUES])
        self.__query = None

    @property
    def values(self) -> Dict:
        return self.state[SELECTED_VALUES]

    @values.setter
    def values(self, v):
        self.state[SELECTED_VALUES] = v

    @property
    def page_idx(self):
        return self.state[PAGE_IDX] or 0

    @page_idx.setter
    def page_idx(self, value):
        self.state[PAGE_IDX] = value

    @property
    def select_all(self):
        return self.state[SELECT_ALL]

    @select_all.setter
    def select_all(self, value):
        self.state[SELECT_ALL] = value

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
        all_items = await self.get_items()
        all_items_len = len(all_items)
        has_pagination = all_items_len > ITEMS_PER_PAGE

        items = all_items[ITEMS_PER_PAGE * self.page_idx: (self.page_idx + 1) * ITEMS_PER_PAGE]

        keyboard = []
        row = []
        for i, item in enumerate(items):
            item_value = item
            data = json.dumps({
                SELECTED_VALUES: i + (self.page_idx * ITEMS_PER_PAGE),
            })
            title = item_value
            if self.values.get(item_value):
                title = f'{title} ✅'
            row.append(InlineKeyboardButton(title, callback_data=data))

            if len(row) == self.desired_amount_of_rows:
                keyboard.append(row)
                row = []
        if len(row):
            keyboard.append(row)

        if has_pagination:
            buttons = []
            if self.page_idx > 0:
                buttons.append(
                    InlineKeyboardButton(f'◀️', callback_data='{"%s": %s}' % (PAGE_IDX, self.page_idx - 1)))
            if self.page_idx < (all_items_len / ITEMS_PER_PAGE - 1):
                buttons.append(InlineKeyboardButton(f'▶️', callback_data='{"%s": %s}' % (PAGE_IDX, self.page_idx + 1)))
            if len(buttons) > 0:
                keyboard.append(buttons)
        return keyboard

    async def build_keyboard(self) -> List[List[InlineKeyboardButton]]:
        """Helper function to build the next inline keyboard."""
        keyboard = await self.build_items_keyboard()

        if self.has_select_all:
            if self.select_all:
                keyboard.append([InlineKeyboardButton(self.unselect_all_text, callback_data='{"%s": 0}' % SELECT_ALL)])
            else:
                keyboard.append([InlineKeyboardButton(self.select_all_text, callback_data='{"%s": 1}' % SELECT_ALL)])
        return keyboard

    #
    async def process_action(self, payload: Payload, update: Update):
        items = await self.get_items()
        if SELECT_ALL in payload.callback:
            self.select_all = payload.callback[SELECT_ALL]
            for key in items:
                self.values[key] = payload.callback[SELECT_ALL]
        elif SELECTED_VALUES in payload.callback:
            key = items[payload.callback[SELECTED_VALUES]]
            self.values[key] = not self.values.get(key)
        elif PAGE_IDX in payload.callback:
            self.page_idx = payload.callback[PAGE_IDX]

        return dict(self.state)

    def has_values(self):
        return len(list(filter(None, self.values.values())))

    def allow_next(self):
        # this method could be overridden at child classes if it needs

        # return len(list(filter(None, self.values.values())))
        return True

    async def build_text(self, is_final=False):
        items = await self.get_items()
        values = 'не вибрано'
        if len(list(filter(None, self.values.values()))):
            values = ', '.join([k for k in items if self.values.get(k)])
        return f'{self.name}: ' + values

    async def get_items(self):
        return []


class ColumnFilter(BaseFilter):
    has_select_all = True

    def get_column(self) -> Column:
        raise NotImplementedError()

    async def get_items(self):
        data = await get_unique_el_from_db(await self.get_query(), self.get_column())
        return data

    @function_logger
    async def build_query(self):
        query = await self.get_query()
        if self.select_all:
            return query

        data = await self.get_items()
        filtered_data = []

        for datum in data:
            if self.values[str(datum)]:
                filtered_data.append(datum)

        if len(filtered_data):
            return query.filter(self.get_column().in_(filtered_data))
        return query.filter()


class DistrictFilter(ColumnFilter):
    name = 'Райони'

    def get_column(self) -> Column:
        return self.model.district


# class AdditionalFilter(BaseFilter):
#     name = 'Додаткові фільтри'
#     has_select_all = False
#
#     async def get_items(self):
#         items = [item for item in ADDITIONAL_FILTERS_MAP.values()]
#         return items

# async def process_action(self, payload: Payload, update: Update):
# filter_name = payload.callback[]
# if filter_name:
#     if not self.values['price_from']:
#         self.values['price_from'] = number
#     elif not self.values['price_to']:
#         self.values['price_to'] = number


class ResidentialComplexFilter(ColumnFilter):
    name = 'ЖК'

    model: Type[Apartments]

    def get_column(self) -> Column:
        return self.model.residential_complex


class RoomsFilter(BaseFilter):
    name = 'Кількість кімнат'

    MAX_ROOMS = 3
    ROOM_BUTTONS_MAPPING = {
        '1': '1️⃣',
        '2': '2️⃣',
        '3': '3️⃣',
        '3+': '➕3️⃣',


    }
    has_select_all = True

    def __init__(self,
                 model: Type[Ad],
                 state: Optional[Dict],
                 prev_filter: Optional['BaseFilter'] = None,
                 name: Optional[str] = None):
        super().__init__(model, state, prev_filter, name)

    async def get_items(self):
        rooms_qty = await self.get_rooms_qty()

        items = []
        for r_qty in range(1, self.MAX_ROOMS):
            if r_qty in rooms_qty:
                items.append(str(r_qty))
                rooms_qty.remove(r_qty)
        if len(rooms_qty):
            items.append(f'{self.MAX_ROOMS}+')

        items = map(lambda x: self.ROOM_BUTTONS_MAPPING.get(x) if x in self.ROOM_BUTTONS_MAPPING else x, items)
        return list(items)

    async def get_rooms_qty(self) -> List[int]:
        return await get_unique_el_from_db(await self.get_query(), self.model.rooms)

    @function_logger
    async def build_query(self):
        rooms_qty = await self.get_rooms_qty()
        items = []
        for r_qty in range(1, self.MAX_ROOMS):
            if self.values[str(r_qty)]:
                items.append(r_qty)
            try:
                rooms_qty.remove(r_qty)
            except ValueError:
                pass

        if self.values[f'➕3️⃣']:
            items += rooms_qty

        query = await self.get_query()
        if len(items):
            return query.filter(self.model.rooms.in_(items))
        return query.filter()


class PriceFilter(BaseFilter):
    name = 'Ціна'
    has_select_all = False

    async def build_text(self, is_final=False):
        to_text = 'до ' + str(self.values['price_to']) + ' грн'
        if not self.has_values() and is_final:
            return f'{self.name}: ' + 'Весь діапазон цін'
        elif not self.values['price_to']:
            return f'{self.name}: ' \
                   f'Надішліть повідомлення з максимальною ціною в гривні ✍'

        else:
            return f'{self.name}: ' + to_text

    async def process_action(self, payload: Payload, update: Update):
        try:
            number = int(payload.message.strip())
            if number:
                if not self.values['price_to']:
                    self.values['price_to'] = number
        except ValueError:
            pass

        if payload.message:
            await update.message.delete()

        return dict(self.state)

    def has_values(self):
        return self.values['price_to']

    def allow_next(self):
        return True

    @function_logger
    async def build_query(self):
        q = await self.get_query()

        if not self.has_values():
            return q.filter()

        price_from = self.values['price_to'] * 0.5
        price_to = self.values['price_to'] * 1.1
        currencies = get_exchange_rates()

        filters = []
        for k, v in currencies.items():
            conditions = [self.model.currency == k]

            if price_from:
                conditions.append(price_from / v <= self.model.rent_price)
            if price_to:
                conditions.append(self.model.rent_price <= (price_to / v))

            f = and_(*conditions)

            filters.append(f)

        q = q.filter(or_(*filters))

        return q


LIVING_AREAS = {
    '< 100м2': [0, 100],
    '100-200м2': [100, 200],
    '200-300м2': [200, 300],
    '> 300м2': [300, 10000],
}


class LivingAreaFilter(BaseFilter):
    name = 'Площа'
    has_select_all = False
    model: Type[Houses]

    async def get_items(self):
        living_areas = list(LIVING_AREAS.keys())
        return living_areas

    @function_logger
    async def build_query(self):
        q = await self.get_query()
        # TODO rewrite better
        area_from = [0]
        area_to = [10000]
        for k, v in LIVING_AREAS.items():
            if self.values[k]:
                area_from.append(v[0])
                area_to.append(v[1])

        area_from_v = min(area_from)
        area_to_v = max(area_to)

        stmt = and_(area_from_v <= self.model.living_area, self.model.living_area <= area_to_v)
        q = q.filter(stmt)
        return q
