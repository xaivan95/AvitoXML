# bot/services/DefaultXMLGenerator.py
import xml.etree.ElementTree as ET
from bot.services.BaseXMLGenerator import BaseXMLGenerator

class DefaultXMLGenerator(BaseXMLGenerator):
    """Генератор XML по умолчанию для товаров без специфичной категории"""

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

        print(f"🔧 DefaultXMLGenerator для товара: '{first_level}' - '{second_level}' - '{third_level}'")

        # Категория
        ET.SubElement(ad, "Category").text = "Одежда, обувь, аксессуары"

        # GoodsType - используем первый уровень категории или "Другое"
        goods_type = first_level if first_level else "Другое"
        ET.SubElement(ad, "GoodsType").text = goods_type

        # Apparel (второй уровень) - ОБЯЗАТЕЛЬНОЕ ПОЛЕ
        apparel_value = self._get_apparel_value(second_level)
        ET.SubElement(ad, "Apparel").text = apparel_value

        # Brand
        brand = product.get('brand', '')
        if brand and brand != 'Не указан':
            ET.SubElement(ad, "Brand").text = brand

        # Size
        size = product.get('size', '')
        if size:
            ET.SubElement(ad, "Size").text = size

        # TargetAudience
        ET.SubElement(ad, "TargetAudience").text = "Частные лица и бизнес"

        return ad

    def _get_apparel_value(self, second_level: str) -> str:
        """Возвращает точное название для Apparel"""
        return second_level if second_level else "Другое"