# bot/services/XMLGeneratorFactory.py
from bot.services.BagsXMLGenerator import BagsXMLGenerator
from bot.services.BaseXMLGenerator import BaseXMLGenerator
from bot.services.ClothingXMLGenerator import ClothingXMLGenerator
from bot.services.MenShoesXMLGenerator import MenShoesXMLGenerator
from bot.services.WomenShoesXMLGenerator import WomenShoesXMLGenerator
from bot.services.AccessoriesXMLGenerator import AccessoriesXMLGenerator

class XMLGeneratorFactory:
    """Фабрика для создания генераторов XML"""

    @staticmethod
    def get_generator(category_name: str) -> BaseXMLGenerator:
        """Получить генератор по названию категории"""
        if not category_name:
            return BaseXMLGenerator()

        category_lower = category_name.lower()

        # Сумки, рюкзаки, чемоданы
        if any(keyword in category_lower for keyword in ["сумк", "рюкзак", "чемодан", "портфел", "борсетк"]):
            return BagsXMLGenerator()

        # Одежда
        elif any(keyword in category_lower for keyword in ["одежда", "мужская", "женская"]):
            return ClothingXMLGenerator()

        # Мужская обувь
        elif "мужская обувь" in category_lower:
            return MenShoesXMLGenerator()

        # Женская обувь
        elif "женская обувь" in category_lower:
            return WomenShoesXMLGenerator()

        # Аксессуары
        elif "аксессуар" in category_lower:
            return AccessoriesXMLGenerator()

        # Обувь (общее)
        elif "обувь" in category_lower:
            # Определяем мужская или женская по контексту
            if "мужск" in category_lower:
                return MenShoesXMLGenerator()
            elif "женск" in category_lower:
                return WomenShoesXMLGenerator()
            else:
                return BaseXMLGenerator()

        else:
            return BaseXMLGenerator()