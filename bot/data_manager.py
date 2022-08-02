from bot.api.google import GoogleApi
from bot.db import remove_data_from_db, add_objects_to_apartments_db, add_objects_to_houses_db
from bot.log import logging
from bot.models import Apartments, Houses

CAT_APARTMENTS = 'Apartments'
CAT_HOUSES = 'Houses'

CATEGORIES = {
    CAT_APARTMENTS: 'Квартири',
    CAT_HOUSES: 'Будинки'
}

PROD_ID = 'id'
PROD_DISTRICT = 'district'
PROD_STREET = 'street'
PROD_RC = 'residential_complex'
PROD_ROOMS = 'rooms'
PROD_RENT_PRICE = 'rent_price'
PROD_CURRENCY = 'currency'
PROD_LINK = 'link'
PROD_PLACING = 'placing'
PROD_LIVING_AREA = 'living_area'
PROD_TERRITORY_AREA = 'territory_area'

MAPPING_APARTS = {
    PROD_ID: '',
    PROD_DISTRICT: 'Район',
    PROD_STREET: 'Вулиця',
    PROD_RC: 'ЖК',
    PROD_ROOMS: 'К',
    PROD_RENT_PRICE: 'Ціна',
    PROD_CURRENCY: 'Вал',
    PROD_LINK: 'Опис',
}
MAPPING_HOUSES = {
    PROD_ID: '№',
    PROD_DISTRICT: 'Район',
    PROD_PLACING: 'Знаходження',
    PROD_ROOMS: 'Кімнат',
    PROD_LIVING_AREA: 'Площа',
    PROD_TERRITORY_AREA: 'Ділянка',
    PROD_RENT_PRICE: 'Ціна',
    PROD_CURRENCY: 'Вал',
    PROD_LINK: 'Опис',
}


class DataManager:

    def __init__(self):
        self.api = GoogleApi()

    async def sync_data(self):
        await self.sync_apartments()
        await self.sync_houses()

        logging.info('Done')

    async def sync_apartments(self):
        await remove_data_from_db(Apartments)
        data = self.api.get_sheet_data(CATEGORIES[CAT_APARTMENTS])

        header = data[0]

        attr_len = len(MAPPING_APARTS)

        diff = set(MAPPING_APARTS.values()) - set(header)

        if diff:
            raise Exception(f'Missing columns: {diff}')

        data = data[1:]

        for datum in data:

            if len(datum) < attr_len:
                logging.warning('Skipped row: %s', datum)
                continue
            print(datum)
            row = {}
            break_status = False
            for i in range(len(header)):

                original_header_name = header[i]

                if i not in range(len(datum)):
                    logging.warning('Skipped row: %s, due to missing column %s', datum, original_header_name)
                    break_status = True
                if break_status:
                    break

                row[original_header_name] = datum[i]

            filtered_obj = {}
            if len(row) != len(header):
                continue
            for k, v in MAPPING_APARTS.items():
                print("K", k, "V", v)
                if row[v] == '':
                    logging.warning('Empty %s property of object. ID: %s | Link: %s', k, row[''], row['Опис'])
                    break
                filtered_obj[k] = row.get(v)

            if len(filtered_obj) != len(MAPPING_APARTS):
                continue
            await add_objects_to_apartments_db(filtered_obj)

    async def sync_houses(self):
        await remove_data_from_db(Houses)
        data = self.api.get_sheet_data(CATEGORIES[CAT_HOUSES])

        header = data[0]

        attr_len = len(MAPPING_HOUSES)

        diff = set(MAPPING_HOUSES.values()) - set(header)

        if diff:
            raise Exception(f'Missing columns: {diff}')

        data = data[1:]

        for datum in data:

            if len(datum) < attr_len:
                logging.warning('Skipped row: %s', datum)
                continue
            print(datum)
            row = {}
            break_status = False
            for i in range(len(header)):

                original_header_name = header[i]

                if i not in range(len(datum)):
                    logging.warning('Skipped row: %s, due to missing column %s', datum, original_header_name)
                    break_status = True
                if break_status:
                    break

                row[original_header_name] = datum[i]

            filtered_obj = {}
            if len(row) != len(header):
                continue
            for k, v in MAPPING_HOUSES.items():
                print("K", k, "V", v)
                if row[v] == '':
                    logging.warning('Empty %s property of object. ID: %s | Link: %s', k, row['№'], row['Опис'])
                    break
                filtered_obj[k] = row.get(v)

            if len(filtered_obj) != len(MAPPING_HOUSES):
                continue
            await add_objects_to_houses_db(filtered_obj)
