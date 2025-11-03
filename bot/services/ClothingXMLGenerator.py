import xml.etree.ElementTree as ET
from xml.dom import minidom
from abc import ABC, abstractmethod
from datetime import datetime
import random

from bot.services.BagsXMLGenerator import BagsXMLGenerator
from bot.services.BaseXMLGenerator import BaseXMLGenerator


class ClothingXMLGenerator(BaseXMLGenerator):
    """Генератор XML для одежды"""

    def generate_ad(self, product: dict, city: str, ad_number: int = 1, metro_station: str = None) -> ET.Element:
        ad = ET.Element("Ad")

        # Добавляем общие элементы
        self._add_common_elements(ad, product, city, ad_number, metro_station)

        # Категория
        ET.SubElement(ad, "Category").text = "Одежда, обувь, аксессуары"

        # GoodsType
        category_name = product.get('category_name', '')
        if "Мужская" in category_name:
            ET.SubElement(ad, "GoodsType").text = "Мужская одежда"
        elif "Женская" in category_name:
            ET.SubElement(ad, "GoodsType").text = "Женская одежда"
        else:
            ET.SubElement(ad, "GoodsType").text = "Одежда"

        # Brand
        brand = product.get('brand', '')
        if brand and brand != 'Не указан':
            ET.SubElement(ad, "Brand").text = brand

        # Size
        clothing_size = product.get('clothing_size', '')
        if clothing_size:
            param = ET.SubElement(ad, "Param")
            ET.SubElement(param, "Name").text = "Размер"
            ET.SubElement(param, "Value").text = clothing_size

        # Color
        clothing_color = product.get('clothing_color', '')
        if clothing_color and clothing_color != "skip":
            color_names = {
                "red": "Красный", "white": "Белый", "pink": "Розовый", "burgundy": "Бордовый",
                "blue": "Синий", "yellow": "Жёлтый", "light_blue": "Голубой", "purple": "Фиолетовый",
                "orange": "Оранжевый", "multicolor": "Разноцветный", "gray": "Серый", "beige": "Бежевый",
                "black": "Чёрный", "brown": "Коричневый", "green": "Зелёный", "silver": "Серебряный",
                "gold": "Золотой"
            }
            param = ET.SubElement(ad, "Param")
            ET.SubElement(param, "Name").text = "Цвет"
            ET.SubElement(param, "Value").text = color_names.get(clothing_color, clothing_color)

        # Material
        clothing_material = product.get('clothing_material', '')
        if clothing_material and clothing_material != "skip":
            param = ET.SubElement(ad, "Param")
            ET.SubElement(param, "Name").text = "Материал"
            ET.SubElement(param, "Value").text = clothing_material

        # TargetAudience
        ET.SubElement(ad, "TargetAudience").text = "Частные лица и бизнес"

        return ad
