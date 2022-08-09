from typing import Literal

import requests
from cachetools.func import ttl_cache

URL = 'https://api.monobank.ua/bank/currency'
USD_CODE = 840
UAH_CODE = 980
EUR_CODE = 978
CURRENCY_MAPPING = {
    'USD': USD_CODE,
    'EUR': EUR_CODE,
}


@ttl_cache(600.0)
def get_exchange_rates():
    r = requests.get(URL)
    response_data = r.json()
    result = {
        'UAH': 1
    }
    for k, v in CURRENCY_MAPPING.items():
        rate = next((item['rateSell'] for item in response_data if
                     (item['currencyCodeA'] == v and item['currencyCodeB'] == UAH_CODE)), None)
        result[k] = rate
    return result
