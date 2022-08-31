import json
from collections import defaultdict
from typing import Dict, List, Optional, Type

from sqlalchemy import or_, and_, Column
from sqlalchemy import select
from sqlalchemy.sql import Select
from telegram import InlineKeyboardButton, Update

from bot.api.monobank_currency import get_exchange_rates
from bot.context.payload import Payload
from bot.data_manager import KIDS_FILTER_TEXT, KIDS_ABOVE_SIX_YO_PROP, DOGS_ALLOWED_PROP, \
    CATS_ALLOWED_PROP, ALL_KIDS_ALLOWED_PROP, PETS_FILTER_TEXT, OTHER_ANIMALS_PROP, \
    ALL_PETS_ALLOWED_PROP
from bot.db import get_unique_el_from_db
from bot.log import logging
from bot.models import Ad, Apartments, Houses
from bot.navigation import NEXT_ADDITIONAL_FILTER, NEXT_BTN, BACK_BTN


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

    def build_next_btn(self):
        next_text = 'Пропустити ➡'
        if self.has_values():
            next_text = 'Далі ➡️'
        return NEXT_BTN(next_text, '{"n":1}')

    def build_back_btn(self):
        return BACK_BTN

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
        items = await self.get_items()
        total_items = len(items)
        selected_items = len(list(filter(None, self.values.values())))
        if self.has_select_all:
            if self.select_all and total_items == selected_items:
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
        return True

    async def build_text(self, is_final=False, is_active=False):
        items = await self.get_items()
        total_items = len(items)
        selected_items = len(list(filter(None, self.values.values())))
        values = 'Не вибрано'
        if total_items == selected_items:
            values = f'Всі {self.name}'
        elif selected_items:
            values = ', '.join([k for k in items if self.values.get(k)])
        return f'<b>{self.name}</b>: ' + values + '\n'

    async def get_items(self):
        return []

    def allow_back(self):
        return True


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
        '3+': '3️⃣+',

    }
    has_select_all = True

    def __init__(self,
                 model: Type[Ad],
                 state: Optional[Dict],
                 prev_filter: Optional['BaseFilter'] = None,
                 name: Optional[str] = None):
        super().__init__(model, state, prev_filter, name)

    async def build_text(self, is_final=False, is_active=False):
        items = await self.get_items()
        selected_items = len(list(filter(None, self.values.values())))
        values = 'Не вибрано'
        if selected_items:
            values = ', '.join([k for k in items if self.values.get(k)])
        return f'<b>{self.name}</b>: ' + values + '\n'

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

        if self.values[f'3️⃣+']:
            items += rooms_qty

        query = await self.get_query()
        if len(items):
            return query.filter(self.model.rooms.in_(items))
        return query.filter()


class AdditionalFilter(BaseFilter):
    name = 'Додаткові фільтри'
    has_select_all = False

    BUTTONS_MAPPING = {
        KIDS_FILTER_TEXT: {
            'question': 'Скільки років Вашій молодшій дитині?',
            'items': [ALL_KIDS_ALLOWED_PROP, KIDS_ABOVE_SIX_YO_PROP],
        },
        PETS_FILTER_TEXT: {
            'question': 'Які в Вас домашні тваринки?',
            'items': [DOGS_ALLOWED_PROP, CATS_ALLOWED_PROP, OTHER_ANIMALS_PROP],
        },
    }

    def allow_next(self):
        return (self.is_first_page() and not self.has_values()) or \
               (self.is_last_page() and self.has_selected_subitems())

    def is_first_page(self):
        return self.page_idx == 0

    def is_last_page(self):
        return self.page_idx == len([el for k, el in self.values.items() if el and k in self.BUTTONS_MAPPING.keys()])

    def has_values(self):
        return super().has_values() > 0

    async def build_keyboard(self) -> List[List[InlineKeyboardButton]]:
        keyboard = []

        if self.is_first_page():
            for k in self.BUTTONS_MAPPING.keys():
                title = k
                if self.values.get(k):
                    title = f'{title} ✅'
                keyboard.append([InlineKeyboardButton(title, callback_data='{"%s": 1}' % k)])
        else:
            items = self.get_active_subitems()
            for k in items:
                title = k
                if self.values.get(k):
                    title = f'{title} ✅'
                keyboard.append([InlineKeyboardButton(title, callback_data='{"%s": 1}' % k)])
        return keyboard

    async def build_text(self, is_final=False, is_active=False):

        active_item = self.get_active_item()
        if is_active:
            if active_item is not None:
                question = self.BUTTONS_MAPPING[active_item]['question']
                return question
        if not self.has_values():
            return None
        text = [f'<b>{self.name}</b>:']
        for key in self.BUTTONS_MAPPING.keys():
            if self.values.get(key):
                selected_subitems = [k for k, v in self.values.items() if v and k in self.BUTTONS_MAPPING[key]['items']]
                if not len(selected_subitems):
                    line = f'--> {key}'
                else:
                    if key == KIDS_FILTER_TEXT:
                        line = f'--> {key} віком: ' + ', '.join(selected_subitems).lower()
                    else:
                        line = f'--> {key}: ' + ', '.join(selected_subitems).lower()
                text.append(line)
        return '\n'.join(text)


    def build_next_btn(self):
        if not self.allow_next() and self.has_selected_subitems():
            return NEXT_BTN(NEXT_ADDITIONAL_FILTER, '{"%s": %s}' % (PAGE_IDX, self.page_idx + 1))
        if not self.has_selected_subitems():
            return None

        return super().build_next_btn()

    def build_back_btn(self):
        if self.page_idx > 0:
            return InlineKeyboardButton(f'◀️', callback_data='{"%s": %s}' % (PAGE_IDX, self.page_idx - 1))
        return super().build_back_btn()

    def get_active_subitems(self):
        active_item = self.get_active_item()
        if active_item is None:
            return []
        return self.BUTTONS_MAPPING[active_item]['items']

    def get_active_item(self):
        if self.is_first_page():
            return None
        active_items = [k for k, v in self.values.items() if v and k in self.BUTTONS_MAPPING.keys()]
        active_item = active_items[self.page_idx - 1]
        return active_item

    #
    @function_logger
    async def build_query(self):
        pets_filter = []
        kids_filter = []
        for k, v in self.values.items():
            if v and k in self.BUTTONS_MAPPING[KIDS_FILTER_TEXT]['items']:
                kids_filter.append(k)
            if v and k in self.BUTTONS_MAPPING[PETS_FILTER_TEXT]['items']:
                pets_filter.append(k)
        filters = []
        conditions = []
        # TODO: REWRITE
        all_kids_filters_selected = len(kids_filter) == len(self.BUTTONS_MAPPING[KIDS_FILTER_TEXT]['items'])
        if KIDS_ABOVE_SIX_YO_PROP in kids_filter and not all_kids_filters_selected:
            kids_filter.append(ALL_KIDS_ALLOWED_PROP)
        conditions.append(self.model.kids.in_(kids_filter))
        if OTHER_ANIMALS_PROP in pets_filter:
            pets_filter.append(ALL_PETS_ALLOWED_PROP)
            pets_filter.remove(OTHER_ANIMALS_PROP)
        conditions.append(self.model.pets.in_(pets_filter))
        f = and_(*conditions)
        filters.append(f)
        q = await self.get_query()
        if not self.has_values():
            return q.filter()
        return q.filter(or_(*filters))

    async def process_action(self, payload: Payload, update: Update):
        items = self.get_active_subitems()
        for k in self.BUTTONS_MAPPING.keys():
            if k in payload.callback:
                self.values[k] = not self.values.get(k)
        for k in items:
            if k in payload.callback:
                self.values[k] = not self.values.get(k)
        if PAGE_IDX in payload.callback:
            self.page_idx = payload.callback[PAGE_IDX]

        return dict(self.state)

    def has_selected_subitems(self):
        if self.page_idx == 0:
            return True
        selected_values = [el for el in self.get_active_subitems() if self.values[el]]
        return len(selected_values) > 0


class PriceFilter(BaseFilter):
    name = 'Ціна'
    has_select_all = False

    async def build_text(self, is_final=False, is_active=False):
        to_text = 'до ' + str(self.values['price_to']) + ' грн'
        if not self.has_values() and is_final:
            return f'<b>{self.name}</b>: ' + 'Весь діапазон цін'
        elif not self.values['price_to']:
            return f'<b>{self.name}</b>: ' \
                   f'<i>Надішліть повідомлення з максимальною ціною в гривні</i> ✍'

        else:
            return f'<b>{self.name}</b>: ' + to_text

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
