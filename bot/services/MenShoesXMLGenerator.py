# bot/services/MenShoesXMLGenerator.py
import xml.etree.ElementTree as ET
from bot.services.BaseXMLGenerator import BaseXMLGenerator

class MenShoesXMLGenerator(BaseXMLGenerator):
    """Генератор XML для мужской обуви"""

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

        print(f"👞 Уровни категории для мужской обуви: '{first_level}' - '{second_level}' - '{third_level}'")

        # Категория
        ET.SubElement(ad, "Category").text = "Одежда, обувь, аксессуары"

        # GoodsType
        ET.SubElement(ad, "GoodsType").text = "Мужская обувь"

        # Apparel (второй уровень) - ОБЯЗАТЕЛЬНОЕ ПОЛЕ
        apparel_value = self._get_apparel_value(second_level)
        ET.SubElement(ad, "Apparel").text = apparel_value

        # Brand
        brand = product.get('brand', '')
        if brand and brand != 'Не указан':
            ET.SubElement(ad, "Brand").text = brand

        # Size (обувной размер)
        shoe_size = product.get('size', '')
        if shoe_size:
            ET.SubElement(ad, "Size").text = shoe_size

        # Color
        shoe_color = product.get('shoe_color', '')
        if shoe_color and shoe_color != "skip":
            color_names = {
                "red": "Красный", "white": "Белый", "pink": "Розовый", "burgundy": "Бордовый",
                "blue": "Синий", "yellow": "Жёлтый", "light_blue": "Голубой", "purple": "Фиолетовый",
                "orange": "Оранжевый", "multicolor": "Разноцветный", "gray": "Серый", "beige": "Бежевый",
                "black": "Чёрный", "brown": "Коричневый", "green": "Зелёный", "silver": "Серебряный",
                "gold": "Золотой"
            }
            ET.SubElement(ad, "Color").text = color_names.get(shoe_color, shoe_color)

        # Material
        shoe_material = product.get('shoe_material', '')
        if shoe_material and shoe_material != "skip":
            ET.SubElement(ad, "Material").text = shoe_material

        # ManufacturerColor (цвет от производителя)
        manufacturer_color = product.get('shoe_manufacturer_color', '')
        if manufacturer_color:
            param = ET.SubElement(ad, "Param")
            ET.SubElement(param, "Name").text = "Цвет"
            ET.SubElement(param, "Value").text = manufacturer_color

        # TargetAudience
        ET.SubElement(ad, "TargetAudience").text = "Частные лица и бизнес"

        return ad

    def _get_apparel_value(self, second_level: str) -> str:
        """Возвращает точное название для Apparel"""
        return second_level if second_level else "Другое"