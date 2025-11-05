import xml.etree.ElementTree as ET
from bot.services.BaseXMLGenerator import BaseXMLGenerator


class BagsXMLGenerator(BaseXMLGenerator):
    """Генератор XML для сумок, рюкзаков и чемоданов"""

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

        print(f"👜 Уровни категории для сумок: '{first_level}' - '{second_level}' - '{third_level}'")

        # Категория
        ET.SubElement(ad, "Category").text = "Одежда, обувь, аксессуары"

        # GoodsType
        ET.SubElement(ad, "GoodsType").text = "Сумки, рюкзаки и чемоданы"

        # Apparel (второй уровень) - ОБЯЗАТЕЛЬНОЕ ПОЛЕ
        apparel_value = self._get_apparel_value(second_level)
        ET.SubElement(ad, "Apparel").text = apparel_value

        # Brand
        brand = product.get('brand', '')
        if brand and brand != 'Не указан':
            ET.SubElement(ad, "Brand").text = brand

        # ApparelType (только для сумок, не для рюкзаков)
        if "рюкзак" not in apparel_value.lower():
            bag_type = product.get('bag_type', '')
            if bag_type:
                apparel_type_names = {
                    "shoulder": "Через плечo",
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

        # Gender
        bag_gender = product.get('bag_gender', '')
        if bag_gender:
            gender_names = {
                "women": "Женщины",
                "men": "Мужчины",
                "unisex": "Унисекс"
            }
            ET.SubElement(ad, "Gender").text = gender_names.get(bag_gender, bag_gender)
        else:
            ET.SubElement(ad, "Gender").text = "Унисекс"

        # TargetAudience
        ET.SubElement(ad, "TargetAudience").text = "Частные лица и бизнес"

        return ad
    def _is_backpack_category(self, category_name: str) -> bool:
        """Проверяет, является ли категория рюкзаком"""
        if not category_name:
            return False

        backpack_keywords = ["рюкзак", "чемоданы", "портфели", "борсетки"]
        return any(keyword in category_name.lower() for keyword in backpack_keywords)
