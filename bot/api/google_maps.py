from urllib.parse import quote_plus

import googlemaps
import requests

from bot import config


class GoogleMapsApi:
    def __init__(self):
        self.gmaps = googlemaps.Client(key=config.G_MAPS_API)

    def get_geodata_by_address(self, address):

        url = f"https://maps.googleapis.com/maps/api/place/findplacefromtext/json?input={quote_plus(address)}&inputtype=textquery&fields=formatted_address%2Cname%2Crating%2Copening_hours%2Cgeometry&key={config.G_MAPS_API}"

        response = requests.request("GET", url, headers={}, data={})

        return_data = None

        data = response.json()
        if len(data['candidates']):
            result = data['candidates'][0]

            if 'geometry' in result and 'location' in result.get('geometry'):
                location = result.get('geometry').get('location')
                return_data = {
                    'google_maps_link': f'https://www.google.com/maps/place/?t=k&q={location["lat"]},{location["lng"]}',
                    'coordinates': location,
                }

            if 'name' in result:
                return_data['google_maps_link'] = f"https://maps.google.com/?t=k&q={quote_plus(address)}"

        return return_data
