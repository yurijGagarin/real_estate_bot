
import httpx
from lxml.html import fromstring


async def get_proxies():
    url = 'https://free-proxy-list.net/'
    async with httpx.AsyncClient() as client:
        r = await client.get(url)
        parser = fromstring(r.text)
    proxies = set()
    for i in parser.xpath('//tbody/tr')[:10]:
        if i.xpath('.//td[7][contains(text(),"yes")]'):
            proxy = ":".join([i.xpath('.//td[1]/text()')[0], i.xpath('.//td[2]/text()')[0]])
            proxies.add(proxy)
    return proxies

