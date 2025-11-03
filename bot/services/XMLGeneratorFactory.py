from bot.services.BagsXMLGenerator import BagsXMLGenerator
from bot.services.BaseXMLGenerator import BaseXMLGenerator
from bot.services.ClothingXMLGenerator import ClothingXMLGenerator


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

        # Обувь
        elif "обувь" in category_lower:
            return BaseXMLGenerator()

        # Аксессуары
        elif "аксессуар" in category_lower:
            return BaseXMLGenerator()

        else:
            return BaseXMLGenerator()