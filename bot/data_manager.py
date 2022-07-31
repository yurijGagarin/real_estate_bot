from pprint import pprint

from bot.api.google import GoogleApi
from bot.log import logging

CAT_APARTMENTS = 'Apartments'

CATEGORIES = {
    CAT_APARTMENTS: 'Квартири'
}

PROD_ID = 'id'
PROD_DISTRICT = 'district'

MAPPING = {
    PROD_ID: '',
    PROD_DISTRICT: 'Район',
}


class DataManager:

    def __init__(self):
        self.api = GoogleApi()

    async def sync_data(self):
        await self.sync_apartments()

        logging.info('Done')

    async def sync_apartments(self):
        data = self.api.get_sheet_data(CATEGORIES[CAT_APARTMENTS])

        header = data[0]

        attr_len = len(MAPPING)

        diff = set(MAPPING.values()) - set(header)
        if diff:
            raise Exception(f'Missing columns: {diff}')

        data = data[1:]

        mapped_data = []

        for datum in data:
            if len(datum) < attr_len:
                logging.warning('Skipped row: %s', datum)
                continue
            print(datum)
            row = {}
            for i in range(len(header)):
                row[header[i]] = datum[i]

            pprint(row)
            break
