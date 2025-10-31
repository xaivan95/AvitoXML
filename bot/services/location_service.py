# bot/services/location_service.py
from typing import List, Dict, Optional
import xml.etree.ElementTree as ET
import random
from .metro_data import generate_metro_address


class LocationService:
    """Сервис для работы с локациями"""

    @staticmethod
    def load_cities_from_xml() -> List[Dict]:
        """Загрузка городов из XML"""
        try:
            tree = ET.parse('cities.xml')
            root = tree.getroot()

            cities = []
            for city_elem in root.findall('city'):
                try:
                    name_elem = city_elem.find('name')
                    population_elem = city_elem.find('population')
                    region_elem = city_elem.find('region')

                    if name_elem is not None and name_elem.text:
                        city_data = {
                            'name': name_elem.text.strip(),
                            'population': int(population_elem.text) if population_elem.text else 0,
                            'region': region_elem.text if region_elem else ''
                        }
                        cities.append(city_data)
                except (ValueError, AttributeError):
                    continue

            cities.sort(key=lambda x: x['population'], reverse=True)
            return cities

        except Exception as e:
            print(f"Error loading cities XML: {e}")
            return LocationService._get_default_cities()

    @staticmethod
    def _get_default_cities() -> List[Dict]:
        """Резервный список городов"""
        return [
            {'name': 'Москва', 'population': 12678079, 'region': 'Москва'},
            {'name': 'Санкт-Петербург', 'population': 5398064, 'region': 'Санкт-Петербург'},
            {'name': 'Новосибирск', 'population': 1625631, 'region': 'Новосибирская область'},
        ]

    @staticmethod
    def get_cities_with_metro() -> List[Dict]:
        """Города с метро"""
        metro_cities = ['Москва', 'Санкт-Петербург', 'Нижний Новгород', 'Новосибирск',
                        'Самара', 'Екатеринбург', 'Казань']

        all_cities = LocationService.load_cities_from_xml()
        return [city for city in all_cities if city['name'] in metro_cities]

    @staticmethod
    def generate_address(city: str, ad_number: int = 1, metro_station: str = None) -> str:
        """Генерация адреса"""
        if metro_station:
            return generate_metro_address(city, metro_station, ad_number)

        # Генерация обычного адреса
        streets = [
            "ул. Ленина", "ул. Центральная", "ул. Советская", "ул. Мира",
            "пр. Победы", "пр. Мира", "бульвар Свободы"
        ]
        street = random.choice(streets)
        building = random.randint(1, 100)

        if ad_number > 1:
            return f"{city}, {street}, д. {building}, кв. {ad_number}"
        return f"{city}, {street}, д. {building}"