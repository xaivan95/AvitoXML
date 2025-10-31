# bot/services/metro_service.py
from aiogram.types import Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from .metro_data import get_metro_cities, get_metro_stations, get_random_stations


class MetroService:
    """Сервис для работы с метро"""

    @staticmethod
    async def ask_metro_city(message: Message, user_name: str = ""):
        """Запрос выбора города с метро"""
        metro_cities = get_metro_cities()

        if not metro_cities:
            await message.answer(
                "❌ В базе данных нет городов с метро.\n"
                "Пожалуйста, выберите другой тип размещения."
            )
            return

        builder = InlineKeyboardBuilder()

        for city in metro_cities:
            stations_count = len(get_metro_stations(city))
            builder.button(
                text=f"🚇 {city} ({stations_count} станций)",
                callback_data=f"metro_city_{city}"
            )

        builder.button(text="🔙 Назад к выбору типа", callback_data="back_to_placement_type")
        builder.adjust(1)

        greeting = f"{user_name}, " if user_name else ""
        await message.answer(
            f"{greeting}выберите город с метро:",
            reply_markup=builder.as_markup()
        )

    @staticmethod
    def get_metro_stations(city: str):
        """Получить станции метро для города"""
        return get_metro_stations(city)

    @staticmethod
    def get_random_stations(city: str, count: int):
        """Получить случайные станции метро"""
        return get_random_stations(city, count)