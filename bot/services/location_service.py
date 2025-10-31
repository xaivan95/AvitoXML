# bot/services/location_service.py
from typing import List, Dict, Optional
import xml.etree.ElementTree as ET
import random

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, Message

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

    @staticmethod
    async def ask_city_input(message: Message, user_name: str = ""):
        """Запрос ввода города по одному"""
        greeting = f"{user_name}, " if user_name else ""

        keyboard = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="✅ Завершить ввод городов")]],
            resize_keyboard=True,
            one_time_keyboard=True
        )

        await message.answer(
            f"{greeting}введите название города:\n\n"
            "🏙️ Город будет проверен и предложен для подтверждения\n"
            "📝 Можно вводить города по одному\n"
            "✅ Нажмите кнопку ниже чтобы завершить",
            reply_markup=keyboard
        )

    @staticmethod
    async def ask_quantity_from_xml(message: Message, user_name: str = ""):
        """Запрос количества объявлений для метода из XML"""
        cities = LocationService.load_cities_from_xml()
        total_cities = len(cities)

        sample_cities = ", ".join([city['name'] for city in cities[:5]])

        greeting = f"{user_name}, " if user_name else ""
        await message.answer(
            f"{greeting}введите количество объявлений (максимум {total_cities}):\n\n"
            f"🏙️ Будут использованы города из базы данных\n"
            f"📊 Всего доступно городов: {total_cities}\n"
            f"📍 Пример: {sample_cities}...\n"
            f"🎯 Будут выбраны города с наибольшим населением"
        )

    @staticmethod
    async def ask_city_selection(message: Message, user_name: str = "", search_query: str = ""):
        """Запрос выбора города из найденных вариантов"""
        greeting = f"{user_name}, " if user_name else ""

        # Здесь должна быть логика поиска городов по запросу
        found_cities = await LocationService.search_cities(search_query)

        if not found_cities:
            await message.answer(
                f"{greeting}город '{search_query}' не найден.\n"
                "Попробуйте ввести другое название:"
            )
            return

        keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
        for city in found_cities[:5]:  # Ограничиваем 5 вариантами
            keyboard.add(KeyboardButton(text=f"📍 {city['name']}"))
        keyboard.add(KeyboardButton(text="🔍 Искать другой город"))

        await message.answer(
            f"{greeting}выберите подходящий вариант:\n\n"
            f"🔍 По запросу: {search_query}\n"
            f"📋 Найдено вариантов: {len(found_cities)}",
            reply_markup=keyboard
        )

    @staticmethod
    async def ask_region_selection(message: Message, user_name: str = ""):
        """Запрос выбора региона для фильтрации городов"""
        regions = LocationService.get_available_regions()

        greeting = f"{user_name}, " if user_name else ""

        keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        buttons = []
        for region in regions[:8]:  # Ограничиваем 8 регионами
            buttons.append(KeyboardButton(text=region))
        keyboard.add(*buttons)
        keyboard.add(KeyboardButton(text="🌍 Все регионы"))

        await message.answer(
            f"{greeting}выберите регион для поиска городов:\n\n"
            f"🗺️ Всего регионов: {len(regions)}\n"
            f"📍 Можно выбрать конкретный регион или все сразу",
            reply_markup=keyboard
        )

    @staticmethod
    async def confirm_city_addition(message: Message, user_name: str = "", city_data: dict = None):
        """Подтверждение добавления города"""
        if not city_data:
            return

        greeting = f"{user_name}, " if user_name else ""

        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="✅ Добавить город"), KeyboardButton(text="❌ Отмена")],
                [KeyboardButton(text="🔄 Ввести другой город")]
            ],
            resize_keyboard=True
        )

        city_info = f"📍 {city_data['name']}"
        if 'region' in city_data:
            city_info += f", {city_data['region']}"
        if 'population' in city_data:
            city_info += f"\n👥 Население: {city_data['population']:,}"

        await message.answer(
            f"{greeting}подтвердите добавление города:\n\n"
            f"{city_info}\n\n"
            f"✅ Добавить этот город в список\n"
            f"❌ Отменить добавление\n"
            f"🔄 Ввести другой город",
            reply_markup=keyboard
        )

    @staticmethod
    async def show_city_summary(message: Message, user_name: str = "", selected_cities: list = None):
        """Показать итоговый список выбранных городов"""
        if not selected_cities:
            selected_cities = []

        greeting = f"{user_name}, " if user_name else ""

        cities_list = "\n".join([f"📍 {city['name']}" for city in selected_cities[:10]])  # Показываем первые 10
        if len(selected_cities) > 10:
            cities_list += f"\n... и ещё {len(selected_cities) - 10} городов"

        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="✅ Начать парсинг"), KeyboardButton(text="✏️ Добавить ещё города")],
                [KeyboardButton(text="🗑️ Очистить список"), KeyboardButton(text="📝 Ввести заново")]
            ],
            resize_keyboard=True
        )

        await message.answer(
            f"{greeting}итоговый список городов:\n\n"
            f"{cities_list}\n\n"
            f"📊 Всего городов: {len(selected_cities)}\n\n"
            f"✅ Начать парсинг с этими городами\n"
            f"✏️ Добавить ещё города\n"
            f"🗑️ Очистить список\n"
            f"📝 Ввести заново",
            reply_markup=keyboard
        )

    @staticmethod
    async def search_cities(query: str) -> list:
        """Поиск городов по запросу"""
        # Реализация поиска городов
        cities = LocationService.load_cities_from_xml()
        return [city for city in cities if query.lower() in city['name'].lower()]

    @staticmethod
    def get_available_regions() -> list:
        """Получение списка доступных регионов"""
        cities = LocationService.load_cities_from_xml()
        regions = list(set(city['region'] for city in cities if 'region' in city))
        return sorted(regions)

    @staticmethod
    async def ask_single_city_for_multiple(message: Message, user_name: str = ""):
        """Запрос одного города для мультиразмещения"""
        greeting = f"{user_name}, " if user_name else ""

        keyboard = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="✅ Завершить ввод городов")]],
            resize_keyboard=True,
            one_time_keyboard=True
        )

        await message.answer(
            f"{greeting}введите название города для мультиразмещения:\n\n"
            "🏙️ Будет создано несколько объявлений в одном городе\n"
            "🔍 Город будет проверен\n"
            "✅ Нажмите кнопку чтобы завершить ввод",
            reply_markup=keyboard
        )

    @staticmethod
    async def ask_city_input(message: Message, user_name: str = ""):
        """Запрос ввода города по одному"""
        greeting = f"{user_name}, " if user_name else ""

        keyboard = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="✅ Завершить ввод городов")]],
            resize_keyboard=True,
            one_time_keyboard=True
        )

        await message.answer(
            f"{greeting}введите название города:\n\n"
            "🏙️ Город будет проверен и предложен для подтверждения\n"
            "📝 Можно вводить города по одному\n"
            "✅ Нажмите кнопку ниже чтобы завершить",
            reply_markup=keyboard
        )

    @staticmethod
    async def ask_quantity_from_xml(message: Message, user_name: str = ""):
        """Запрос количества объявлений для метода из XML"""
        cities = LocationService.load_cities_from_xml()
        total_cities = len(cities)

        sample_cities = ", ".join([city['name'] for city in cities[:5]])

        greeting = f"{user_name}, " if user_name else ""
        await message.answer(
            f"{greeting}введите количество объявлений (максимум {total_cities}):\n\n"
            f"🏙️ Будут использованы города из базы данных\n"
            f"📊 Всего доступно городов: {total_cities}\n"
            f"📍 Пример: {sample_cities}...\n"
            f"🎯 Будут выбраны города с наибольшим населением"
        )