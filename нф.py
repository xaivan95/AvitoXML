import aiohttp
import urllib.parse


async def validate_city_nominatim(city_name: str) -> dict:
    """Проверка города через Nominatim (OpenStreetMap)"""
    encoded_city = urllib.parse.quote(city_name)
    url = f"https://nominatim.openstreetmap.org/search"

    params = {
        'q': f"{city_name}, Россия",
        'format': 'json',
        'addressdetails': 1,
        'limit': 1,
        'accept-language': 'ru'
    }

    headers = {
        'User-Agent': 'YourBot/1.0 (your@email.com)'  # Обязательно укажите User-Agent
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()

                    if data:
                        result = data[0]
                        address = result.get('address', {})

                        city_info = {
                            'name': address.get('city') or address.get('town') or address.get('village') or city_name,
                            'full_address': result.get('display_name', ''),
                            'lat': result.get('lat'),
                            'lon': result.get('lon'),
                            'type': result.get('type')
                        }
                        return {'valid': True, 'data': city_info}

        return {'valid': False, 'error': 'Город не найден'}

    except Exception as e:
        return {'valid': False, 'error': f'Ошибка API: {str(e)}'}
