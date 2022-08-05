import bot
from bot.api.google import GoogleApi
from bot.db import remove_data_from_db, add_objects_to_db
from bot.log import logging
from bot.models import Apartments, Houses

CAT_APARTMENTS = 'Apartments'
CAT_HOUSES = 'Houses'

CATEGORIES = {
    CAT_APARTMENTS: 'Квартири',
    CAT_HOUSES: 'Будинки'
}

PROP_ID = 'id'
PROP_DISTRICT = 'district'
PROP_STREET = 'street'
PROP_RC = 'residential_complex'
PROP_ROOMS = 'rooms'
PROP_RENT_PRICE = 'rent_price'
PROP_CURRENCY = 'currency'
PROP_LINK = 'link'
PROP_PLACING = 'placing'
PROP_LIVING_AREA = 'living_area'
PROP_TERRITORY_AREA = 'territory_area'
PROP_IS_CLOSED = 'is_closed'


def validate_link(v):
    if v and v.startswith('https://t.me'):
        return v
    raise ValueError('Invalid link')


def validated_is_closed(v):
    if v:
        raise ValueError


def validate_currency(v):
    if v in ['EUR', 'UAH', 'USD']:
        return v
    raise ValueError('Invalid currency')


VALIDATORS = {
    PROP_ID: int,
    PROP_ROOMS: lambda v: int(v.replace(' ', '')),
    PROP_LIVING_AREA: lambda v: int(v.replace(' ', '')),
    PROP_TERRITORY_AREA: lambda v: int(v.replace(' ', '')),
    PROP_RENT_PRICE: lambda v: int(v.replace(' ', '')),
    PROP_CURRENCY: validate_currency,
    PROP_IS_CLOSED: validated_is_closed,
    PROP_LINK: validate_link,
}

MAPPING_APARTS = {
    '': PROP_ID,
    'Район': PROP_DISTRICT,
    'Вулиця': PROP_STREET,
    'ЖК': PROP_RC,
    'К': PROP_ROOMS,
    'Ціна': PROP_RENT_PRICE,
    'Вал': PROP_CURRENCY,
    'Опис': PROP_LINK,
    'Актуальність': PROP_IS_CLOSED,
}
MAPPING_HOUSES = {
    '№': PROP_ID,
    'Район': PROP_DISTRICT,
    'Знаходження': PROP_PLACING,
    'Кімнат': PROP_ROOMS,
    'Площа': PROP_LIVING_AREA,
    'Ділянка': PROP_TERRITORY_AREA,
    'Ціна': PROP_RENT_PRICE,
    'Вал': PROP_CURRENCY,
    'Опис': PROP_LINK,
    'Актуальність': PROP_IS_CLOSED,
}


class DataManager:

    def __init__(self):
        self.api = GoogleApi()

    async def sync_data(self):
        await self.sync_apartments()
        # await self.sync_houses()

        logging.info('Done')

    def get_sheet_data(self, sheet_name, mapping):
        """
        :param sheet_name: str
        :param mapping: Dict
        :return: List[Dict]
        """
        data = self.api.get_sheet_data(sheet_name)

        header = data[0]
        header_len = len(header)

        mapping_len = len(mapping)

        diff = set(mapping.keys()) - set(header)

        if diff:
            raise Exception(f'Missing columns: {diff}')

        data = data[1:]

        result = []
        for datum in data:
            datum_len = len(datum)
            if datum_len < mapping_len:
                logging.warning('Skipped row: %s', datum)
                continue

            print(datum)
            result_row = {}
            for col_idx in range(header_len):
                original_header_name = header[col_idx]
                if original_header_name not in mapping:
                    continue
                attr_name = mapping[original_header_name]

                value = datum[col_idx] if col_idx < datum_len else None

                validator = VALIDATORS.get(attr_name)
                try:
                    if validator:
                        value = validator(value)
                except (ValueError, TypeError) as e:
                    logging.warning('Error with property %s of row: %s', original_header_name, datum)
                    break

                if value is not None:
                    result_row[attr_name] = value
            else:
                result.append(result_row)

        return result

    async def sync_apartments(self):
        data = self.get_sheet_data(CATEGORIES[CAT_APARTMENTS], MAPPING_APARTS)

        await remove_data_from_db(Apartments)
        await add_objects_to_db(bot.models.Apartments, data)

    async def sync_houses(self):
        data = self.get_sheet_data(CATEGORIES[CAT_HOUSES], MAPPING_HOUSES)

        await remove_data_from_db(Houses)
        await add_objects_to_db(bot.models.Houses, data)
