from typing import Literal

import requests

URL = 'https://api.monobank.ua/bank/currency'
USD_CODE = 840
UAH_CODE = 980
EUR_CODE = 978


async def get_exchange_rate(currency: Literal['USD', 'EUR']):
    currencyCodeB = UAH_CODE
    r = requests.get(URL)
    result = r.json()
    if currency == 'USD':
        currencyCodeA = USD_CODE

    elif currency == 'EUR':
        currencyCodeA = EUR_CODE

    else:
        return "unsupported currency"
    my_rate = next((item['rateSell'] for item in result if (item['currencyCodeA'] == currencyCodeA
                                                            and item['currencyCodeB'] == currencyCodeB)),
                   None)
    return my_rate

