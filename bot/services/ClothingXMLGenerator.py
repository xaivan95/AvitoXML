import xml.etree.ElementTree as ET
from xml.dom import minidom
from abc import ABC, abstractmethod
from datetime import datetime
import random

from bot.services.BagsXMLGenerator import BagsXMLGenerator
from bot.services.BaseXMLGenerator import BaseXMLGenerator


class ClothingXMLGenerator(BaseXMLGenerator):
    """Генератор XML для одежды"""

    def generate_ad(self, product: dict, city: str, ad_number: int = 1, metro_station: str = None,
                    images_map: dict = None) -> ET.Element:
        ad = ET.Element("Ad")

        # Добавляем общие элементы
        self._add_common_elements(ad, product, city, ad_number, metro_station)

        # Добавляем изображения с правильными именами
        if images_map is not None:
            self._add_images_to_ad(ad, product, ad_number, images_map)
        else:
            # Резервный вариант без images_map
            self._add_images(ad, product)

        # Извлекаем уровни категории
        first_level, second_level, third_level = self._extract_category_levels(product)

        print(f"🔍 Уровни категории: '{first_level}' - '{second_level}' - '{third_level}'")

        # Категория (всегда одинаковая)
        ET.SubElement(ad, "Category").text = "Одежда, обувь, аксессуары"

        # GoodsType (первый уровень)
        goods_type = self._get_goodstype_value(first_level)
        ET.SubElement(ad, "GoodsType").text = goods_type

        # Apparel (второй уровень) - ОБЯЗАТЕЛЬНОЕ ПОЛЕ
        apparel_value = self._get_apparel_value(second_level)
        ET.SubElement(ad, "Apparel").text = apparel_value

        # DressType (третий уровень) - если есть
        dress_type = self._get_dresstype_value(third_level)
        if dress_type:
            ET.SubElement(ad, "DressType").text = dress_type

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

    def _get_goodstype_value(self, first_level: str) -> str:
        """Преобразует первый уровень категории в значение для GoodsType"""
        if not first_level:
            return "Одежда"

        # Используем точное название первого уровня
        return first_level

    def _get_apparel_value(self, second_level: str) -> str:
        """Возвращает точное название для Apparel"""
        return second_level if second_level else "Другое"

    def _get_dresstype_value(self, third_level: str) -> str:
        """Возвращает точное название для DressType"""
        return third_level
