from pprint import pprint

from bot.api.google import GoogleApi
from bot.db import remove_data_from_db, add_objects_from_mapping_to_db
from bot.log import logging
from bot.models import Apartments

CAT_APARTMENTS = 'Apartments'

CATEGORIES = {
    CAT_APARTMENTS: 'Квартири'
}

PROD_ID = 'id'
PROD_DISTRICT = 'district'
PROD_STREET = 'street'
PROD_RC = 'residential_complex'
PROD_ROOMS = 'rooms'
PROD_RENT_PRICE = 'rent_price'
PROD_CURRENCY = 'currency'
PROD_LINK = 'link'

MAPPING = {
    PROD_ID: '',
    PROD_DISTRICT: 'Район',
    PROD_STREET: 'Вулиця',
    PROD_RC: 'ЖК',
    PROD_ROOMS: 'К',
    PROD_RENT_PRICE: 'Ціна',
    PROD_CURRENCY: 'Вал',
    PROD_LINK: 'Опис',
}


class DataManager:

    def __init__(self):
        self.api = GoogleApi()

    async def sync_data(self):
        await self.sync_apartments()

        logging.info('Done')

    async def sync_apartments(self):
        await remove_data_from_db(Apartments)
        data = self.api.get_sheet_data(CATEGORIES[CAT_APARTMENTS])

        header = data[0]

        attr_len = len(MAPPING)

        diff = set(MAPPING.values()) - set(header)

        if diff:
            raise Exception(f'Missing columns: {diff}')

        data = data[1:]

        mapped_data = []
        j = 0
        for datum in data:

            if len(datum) < attr_len:
                logging.warning('Skipped row: %s', datum)
                continue
            print(datum)
            j += 1
            row = {}
            break_status = False
            for i in range(len(header)):

                original_header_name = header[i]

                if i not in range(len(datum)):
                    logging.warning('Skipped row: %s, due to missing column %s', datum, original_header_name)
                    break_status = True
                # if len(datum[i]) == 0:
                #                 #     logging.warning('Skipped row: %s, due to missing value %s', datum, i)
                #                 #     break_status = True
                if break_status:
                    break

                row[original_header_name] = datum[i]
            # if break_status:
            #     break
            #
            # if j == 17:
            #     break
            # pprint(row)

            # # TODO check if len(row) == len(header)

            filtered_obj = {}
            if len(row) != len(header):
                continue
            for k, v in MAPPING.items():
                print("K", k, "V", v)
                if row[v] == '':
                    logging.warning('Empty %s property of object. ID: %s | Link: %s', k, row[''], row['Опис'])
                    break
                filtered_obj[k] = row.get(v)

            if len(filtered_obj) != len(MAPPING):
                continue
            await add_objects_from_mapping_to_db(Apartments, filtered_obj)

            # pprint(filtered_obj)
            #
            # pprint(row)

            # TODO: map #2
