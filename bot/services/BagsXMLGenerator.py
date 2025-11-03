import xml.etree.ElementTree as ET
from bot.services.BaseXMLGenerator import BaseXMLGenerator


class BagsXMLGenerator(BaseXMLGenerator):
    """Генератор XML для сумок, рюкзаков и чемоданов"""

    def generate_ad(self, product: dict, city: str, ad_number: int = 1, metro_station: str = None) -> ET.Element:
        ad = ET.Element("Ad")

        # Добавляем общие элементы
        self._add_common_elements(ad, product, city, ad_number, metro_station)

        # Категория
        ET.SubElement(ad, "Category").text = "Одежда, обувь, аксессуары"

        # GoodsType
        ET.SubElement(ad, "GoodsType").text = "Сумки, рюкзаки и чемоданы"

        # Brand
        brand = product.get('brand', '')
        if brand and brand != 'Не указан':
            ET.SubElement(ad, "Brand").text = brand

        # Apparel и ApparelType
        category_name = product.get('category_name', '')
        is_backpack = self._is_backpack_category(category_name)

        if is_backpack:
            ET.SubElement(ad, "Apparel").text = "Рюкзаки"
            # Для рюкзаков ApparelType не требуется
        else:
            ET.SubElement(ad, "Apparel").text = "Сумки"
            # ApparelType для сумок
            bag_type = product.get('bag_type', '')
            if bag_type:
                apparel_type_names = {
                    "shoulder": "Через плечо",
                    "crossbody": "Кросс-боди",
                    "sport": "Спортивная",
                    "clutch": "Клатч",
                    "waist": "Поясная",
                    "shopper": "Шопер",
                    "beach": "Пляжная",
                    "with_handles": "С ручками",
                    "accessory": "Аксессуар для сумки"
                }
                ET.SubElement(ad, "ApparelType").text = apparel_type_names.get(bag_type, bag_type)

        # Material
        bag_material = product.get('bag_material', '')
        if bag_material and bag_material != "skip":
            material_names = {
                "natural_leather": "Натуральная кожа",
                "artificial_leather": "Искусственная кожа",
                "other": "Другой"
            }
            ET.SubElement(ad, "Material").text = material_names.get(bag_material, bag_material)

        # Color
        bag_color = product.get('bag_color', '')
        if bag_color and bag_color != "skip":
            color_names = {
                "red": "Красный", "white": "Белый", "pink": "Розовый", "burgundy": "Бордовый",
                "blue": "Синий", "yellow": "Жёлтый", "light_blue": "Голубой", "purple": "Фиолетовый",
                "orange": "Оранжевый", "multicolor": "Разноцветный", "gray": "Серый", "beige": "Бежевый",
                "black": "Чёрный", "brown": "Коричневый", "green": "Зелёный", "silver": "Серебряный",
                "gold": "Золотой"
            }
            ET.SubElement(ad, "Color").text = color_names.get(bag_color, bag_color)

        # Gender - ДОБАВЛЕНО ОБЯЗАТЕЛЬНОЕ ПОЛЕ
        bag_gender = product.get('bag_gender', '')
        if bag_gender:
            gender_names = {
                "women": "Женщины",
                "men": "Мужчины",
                "unisex": "Унисекс"
            }
            ET.SubElement(ad, "Gender").text = gender_names.get(bag_gender, bag_gender)
        else:
            # Значение по умолчанию, если не указано
            ET.SubElement(ad, "Gender").text = "Унисекс"

        # TargetAudience (по умолчанию)
        ET.SubElement(ad, "TargetAudience").text = "Частные лица и бизнес"

        return ad

    def _is_backpack_category(self, category_name: str) -> bool:
        """Проверяет, является ли категория рюкзаком"""
        if not category_name:
            return False

        backpack_keywords = ["рюкзак", "чемоданы", "портфели", "борсетки"]
        return any(keyword in category_name.lower() for keyword in backpack_keywords)
