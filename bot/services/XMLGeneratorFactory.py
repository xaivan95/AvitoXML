# bot/services/XMLGeneratorFactory.py
from bot.services.BaseXMLGenerator import BaseXMLGenerator

class XMLGeneratorFactory:
    """Фабрика для создания генераторов XML"""

    @staticmethod
    def get_generator(category_name: str) -> BaseXMLGenerator:
        """Получить генератор по названию категории"""
        if not category_name:
            print("⚠️ Категория не указана, используем DefaultXMLGenerator")
            from bot.services.DefaultXMLGenerator import DefaultXMLGenerator
            return DefaultXMLGenerator()

        category_lower = category_name.lower()
        print(f"🔍 Определение генератора для категории: '{category_name}'")

        # Аксессуары
        if any(keyword in category_lower for keyword in ["аксессуар", "аксесуар"]):
            print("✅ Используем AccessoriesXMLGenerator")
            from bot.services.AccessoriesXMLGenerator import AccessoriesXMLGenerator
            return AccessoriesXMLGenerator()

        # Сумки, рюкзаки, чемоданы
        elif any(keyword in category_lower for keyword in ["сумк", "рюкзак", "чемодан", "портфел", "борсетк"]):
            print("✅ Используем BagsXMLGenerator")
            from bot.services.BagsXMLGenerator import BagsXMLGenerator
            return BagsXMLGenerator()

        # Мужская обувь
        elif "мужская обувь" in category_lower:
            print("✅ Используем MenShoesXMLGenerator")
            from bot.services.MenShoesXMLGenerator import MenShoesXMLGenerator
            return MenShoesXMLGenerator()

        # Женская обувь
        elif "женская обувь" in category_lower:
            print("✅ Используем WomenShoesXMLGenerator")
            from bot.services.WomenShoesXMLGenerator import WomenShoesXMLGenerator
            return WomenShoesXMLGenerator()

        # Одежда
        elif any(keyword in category_lower for keyword in ["одежда", "мужская одежда", "женская одежда"]):
            print("✅ Используем ClothingXMLGenerator")
            from bot.services.ClothingXMLGenerator import ClothingXMLGenerator
            return ClothingXMLGenerator()

        # Обувь (общее)
        elif "обувь" in category_lower:
            # Определяем мужская или женская по контексту
            if "мужск" in category_lower:
                print("✅ Используем MenShoesXMLGenerator (по контексту)")
                from bot.services.MenShoesXMLGenerator import MenShoesXMLGenerator
                return MenShoesXMLGenerator()
            elif "женск" in category_lower:
                print("✅ Используем WomenShoesXMLGenerator (по контексту)")
                from bot.services.WomenShoesXMLGenerator import WomenShoesXMLGenerator
                return WomenShoesXMLGenerator()
            else:
                print("⚠️ Используем DefaultXMLGenerator для неопределенной обуви")
                from bot.services.DefaultXMLGenerator import DefaultXMLGenerator
                return DefaultXMLGenerator()

        else:
            print(f"⚠️ Используем DefaultXMLGenerator (категория '{category_name}' не распознана)")
            from bot.services.DefaultXMLGenerator import DefaultXMLGenerator
            return DefaultXMLGenerator()