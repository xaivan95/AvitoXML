import config
from typing import Dict, Tuple, Optional


class CategoryService:
    """Сервис для работы с категориями Avito"""

    @staticmethod
    def get_category_by_id(category_id: str) -> Optional[Dict]:
        """Получает категорию по ID"""
        categories = config.AVITO_CATEGORIES

        # Ищем в основных категориях
        if category_id in categories:
            return categories[category_id]

        # Ищем в подкатегориях
        for main_cat in categories.values():
            if 'subcategories' in main_cat:
                for sub_id, sub_cat in main_cat['subcategories'].items():
                    if sub_id == category_id:
                        return sub_cat if isinstance(sub_cat, dict) else {'name': sub_cat}
                    # Ищем в под-подкатегориях
                    if isinstance(sub_cat, dict) and 'subcategories' in sub_cat:
                        for subsub_id, subsub_cat in sub_cat['subcategories'].items():
                            if subsub_id == category_id:
                                return {'name': subsub_cat}

        return None

    @staticmethod
    def get_category_levels(category_id: str) -> Tuple[str, str, str]:
        """
        Возвращает уровни категории: (first_level, second_level, third_level)
        """
        if not category_id:
            return "", "", ""

        categories = config.AVITO_CATEGORIES

        print(f"🔍 Поиск категории по ID: {category_id}")

        # Ищем категорию и ее родителей
        for main_id, main_cat in categories.items():
            main_name = main_cat['name']

            # Проверяем основные категории
            if category_id == main_id:
                print(f"✅ Найдена основная категория: {main_name}")
                return main_name, "", ""

            # Ищем в подкатегориях
            if 'subcategories' in main_cat:
                for sub_id, sub_cat in main_cat['subcategories'].items():
                    # Определяем название подкатегории
                    if isinstance(sub_cat, dict):
                        sub_name = sub_cat['name']
                    else:
                        sub_name = sub_cat

                    if category_id == sub_id:
                        print(f"✅ Найдена подкатегория: {main_name} - {sub_name}")
                        return main_name, sub_name, ""

                    # Ищем в под-подкатегориях
                    if isinstance(sub_cat, dict) and 'subcategories' in sub_cat:
                        for subsub_id, subsub_name in sub_cat['subcategories'].items():
                            if category_id == subsub_id:
                                print(f"✅ Найдена под-подкатегория: {main_name} - {sub_name} - {subsub_name}")
                                return main_name, sub_name, subsub_name

        print(f"❌ Категория с ID {category_id} не найдена")
        return "", "", ""

    @staticmethod
    def get_category_levels_from_name(category_name: str) -> Tuple[str, str, str]:
        """
        Извлекает уровни категории из названия
        """
        if not category_name:
            return "", "", ""

        print(f"🔍 Разбор названия категории: '{category_name}'")

        # Разделяем по дефисам
        parts = [part.strip() for part in category_name.split('-')]

        first_level = parts[0] if len(parts) > 0 else ""
        second_level = parts[1] if len(parts) > 1 else ""
        third_level = parts[2] if len(parts) > 2 else ""

        print(f"✅ Разобрано: '{first_level}' - '{second_level}' - '{third_level}'")

        return first_level, second_level, third_level

    @staticmethod
    def get_avito_category_id(category_id: str) -> str:
        """Получает ID категории для Avito"""
        return config.CATEGORY_IDS.get(category_id, "")

    @staticmethod
    def get_apparel_value(second_level: str) -> str:
        """Возвращает точное название второго уровня для Apparel"""
        return second_level if second_level else "Другое"

    @staticmethod
    def get_dresstype_value(third_level: str) -> str:
        """Возвращает точное название третьего уровня для DressType"""
        return third_level if third_level else ""