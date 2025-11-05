# bot/services/AccessoriesXMLGenerator.py
import xml.etree.ElementTree as ET
from bot.services.BaseXMLGenerator import BaseXMLGenerator

class AccessoriesXMLGenerator(BaseXMLGenerator):
    """Генератор XML для аксессуаров"""

    def generate_ad(self, product: dict, city: str, ad_number: int = 1, metro_station: str = None,
                    images_map: dict = None) -> ET.Element:
        ad = ET.Element("Ad")

        # Добавляем общие элементы
        self._add_common_elements(ad, product, city, ad_number, metro_station)

        # Добавляем изображения с правильными именами
        if images_map is not None:
            self._add_images_to_ad(ad, product, ad_number, images_map)
        else:
            self._add_images(ad, product)

        # Извлекаем уровни категории
        first_level, second_level, third_level = self._extract_category_levels(product)

        print(f"👓 Уровни категории для аксессуаров: '{first_level}' - '{second_level}' - '{third_level}'")

        # Категория
        ET.SubElement(ad, "Category").text = "Одежда, обувь, аксессуары"

        # GoodsType
        ET.SubElement(ad, "GoodsType").text = "Аксессуары"

        # Apparel (второй уровень) - ОБЯЗАТЕЛЬНОЕ ПОЛЕ
        apparel_value = self._get_apparel_value(second_level)
        ET.SubElement(ad, "Apparel").text = apparel_value

        # Brand
        brand = product.get('brand', '')
        if brand and brand != 'Не указан':
            ET.SubElement(ad, "Brand").text = brand

        # Color
        accessory_color = product.get('accessory_color', '')
        if accessory_color and accessory_color != "skip":
            color_names = {
                "red": "Красный", "white": "Белый", "pink": "Розовый", "burgundy": "Бордовый",
                "blue": "Синий", "yellow": "Жёлтый", "light_blue": "Голубой", "purple": "Фиолетовый",
                "orange": "Оранжевый", "multicolor": "Разноцветный", "gray": "Серый", "beige": "Бежевый",
                "black": "Чёрный", "brown": "Коричневый", "green": "Зелёный", "silver": "Серебряный",
                "gold": "Золотой"
            }
            ET.SubElement(ad, "Color").text = color_names.get(accessory_color, accessory_color)

        # Gender (Для кого)
        accessory_gender = product.get('accessory_gender', '')
        if accessory_gender:
            gender_names = {
                "women": "Женщины",
                "men": "Мужчины",
                "unisex": "Унисекс"
            }
            ET.SubElement(ad, "Gender").text = gender_names.get(accessory_gender, accessory_gender)

        # TargetAudience
        ET.SubElement(ad, "TargetAudience").text = "Частные лица и бизнес"

        return ad

    def _get_apparel_value(self, second_level: str) -> str:
        """Возвращает точное название для Apparel"""
        return second_level if second_level else "Другое"