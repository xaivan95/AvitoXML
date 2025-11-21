# bot/services/xml_generator.py
import os
import shutil
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from io import BytesIO
from xml.dom import minidom
from abc import ABC, abstractmethod
from datetime import datetime
import random

import requests

from bot.services.category_service import CategoryService


class BaseXMLGenerator(ABC):
    """Базовый класс для генерации XML"""

    def __init__(self, image_service=None):
        self.format_version = "3"
        self.target = "Avito.ru"
        self.image_service = image_service

    def _add_delivery_to_ad(self, ad: ET.Element, product: dict):
        """Добавление информации о доставке в объявление"""
        delivery_services = product.get('delivery_services', [])

        if not delivery_services or "disabled" in delivery_services:
            return

        delivery_elem = ET.SubElement(ad, "Delivery")

        # Маппинг кодов доставки на значения Avito
        delivery_mapping = {
            "pickup": "ПВЗ",
            "courier": "Курьер",
            "postamat": "Постамат",
            "own_courier": "Свой курьер",
            "sdek": "Свой партнер СДЭК",
            "business_lines": "Свой партнер Деловые Линии",
            "dpd": "Свой партнер DPD",
            "pek": "Свой партнер ПЭК",
            "russian_post": "Свой партнер Почта России",
            "sdek_courier": "Свой партнер СДЭК курьер",
            "self_pickup_online": "Самовывоз с онлайн-оплатой"
        }

        for service_code in delivery_services:
            if service_code in delivery_mapping and service_code != "disabled":
                ET.SubElement(delivery_elem, "Option").text = delivery_mapping[service_code]

        # Добавляем скидку на доставку если есть
        delivery_discount = product.get('delivery_discount', '')
        delivery_discount_percent = product.get('delivery_discount_percent')

        if delivery_discount == "free":
            # Бесплатная доставка
            discount_elem = ET.SubElement(delivery_elem, "Discount")
            ET.SubElement(discount_elem, "Type").text = "free"
        elif delivery_discount == "discount" and delivery_discount_percent:
            # Скидка с процентом
            discount_elem = ET.SubElement(delivery_elem, "Discount")
            ET.SubElement(discount_elem, "Type").text = "percent"
            ET.SubElement(discount_elem, "Value").text = str(delivery_discount_percent)

    @abstractmethod
    def generate_ad(self, product: dict, city: str, ad_number: int = 1, metro_station: str = None, images_map: dict = None) -> ET.Element:
        """Генерация элемента объявления с поддержкой images_map"""
        pass

    def generate_xml_content(self, products: list, images_map: dict = None) -> str:
        """Генерация XML контента с правильными изображениями для каждого объявления"""
        root = ET.Element("Ads",
                          formatVersion=self.format_version,
                          target=self.target)

        ad_count = 0

        for product in products:
            # Для КАЖДОГО товара определяем свой генератор
            category_name = product.get('category_name', '')
            from bot.services.XMLGeneratorFactory import XMLGeneratorFactory
            generator = XMLGeneratorFactory.get_generator(category_name)

            # Настраиваем generator так же как основной
            generator.image_service = self.image_service

            print(f"🔧 Используем генератор {generator.__class__.__name__} для товара: {category_name}")

            # Получаем города для размещения
            cities = product.get('cities', [])
            quantity = product.get('quantity', 1)
            placement_method = product.get('placement_method', 'exact_cities')

            # Создаем объявления в зависимости от метода размещения
            if placement_method == 'multiple_in_city' and cities:
                # Мультиразмещение в одном городе
                for i in range(quantity):
                    ad = generator.generate_ad(product, cities[0], i + 1, None, images_map)
                    root.append(ad)
                    ad_count += 1

            elif placement_method == 'by_quantity' and cities:
                # Размещение по количеству в разных городах
                for i in range(min(quantity, len(cities))):
                    city = cities[i] if i < len(cities) else cities[0]
                    ad = generator.generate_ad(product, city, i + 1, None, images_map)
                    root.append(ad)
                    ad_count += 1

            elif placement_method == 'metro' and product.get('selected_metro_stations'):
                # Размещение по станциям метро
                metro_stations = product.get('selected_metro_stations', [])
                metro_city = product.get('metro_city', 'Москва')

                for i, station in enumerate(metro_stations[:quantity]):
                    ad = generator.generate_ad(product, metro_city, i + 1, station, images_map)
                    root.append(ad)
                    ad_count += 1

            else:
                # Обычное размещение по городам
                for i, city in enumerate(cities[:quantity]):
                    ad = generator.generate_ad(product, city, i + 1, None, images_map)
                    root.append(ad)
                    ad_count += 1

        # Добавляем информацию о количестве объявлений
        ET.SubElement(root, "TotalAds").text = str(ad_count)

        # Конвертируем в красивый XML
        rough_string = ET.tostring(root, encoding='utf-8')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ")

    async def generate_zip_archive(self, products: list) -> BytesIO:
        """Генерация ZIP архива с XML и изображениями"""
        temp_dir = tempfile.mkdtemp()

        try:
            zip_buffer = BytesIO()

            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                # Сначала собираем все уникальные изображения для архива
                all_images_map = {}  # {image_url: filename}
                image_counter = 1

                # Проходим по всем товарам и собираем изображения
                for product in products:
                    images = self._get_product_images_for_archive(product)
                    for img_url in images:
                        if img_url and img_url not in all_images_map:
                            filename = f"{image_counter}.jpg"
                            all_images_map[img_url] = filename
                            image_counter += 1

                print(f"📸 Всего уникальных изображений для архива: {len(all_images_map)}")

                # Скачиваем и добавляем изображения в архив
                successful_downloads = 0
                for img_url, filename in all_images_map.items():
                    try:
                        image_path = os.path.join(temp_dir, filename)

                        print(f"⬇️ Скачиваем изображение {filename}: {img_url[:50]}...")

                        if self.image_service:
                            image_content = await self.image_service.process_image_for_export(img_url)
                            if image_content:
                                with open(image_path, 'wb') as f:
                                    f.write(image_content)

                                zip_file.write(image_path, filename)
                                successful_downloads += 1

                        else:
                            # Логика для URL без image_service
                            if self._is_url(img_url):
                                response = requests.get(img_url, timeout=30, stream=True)
                                if response.status_code == 200:
                                    with open(image_path, 'wb') as f:
                                        for chunk in response.iter_content(chunk_size=8192):
                                            f.write(chunk)

                                    zip_file.write(image_path, filename)
                                    successful_downloads += 1

                                else:
                                    print(f"❌ Ошибка скачивания {filename}: статус {response.status_code}")

                    except Exception as e:
                        print(f"❌ Ошибка при обработке изображения {filename}: {e}")
                        continue

                print(f"✅ В архив добавлено {successful_downloads} изображений")

                # Теперь генерируем XML с правильными ссылками на изображения
                xml_content = self.generate_xml_content(products, all_images_map)
                zip_file.writestr('avito.xml', xml_content.encode('utf-8'))

                # README - исправленный вызов
                readme_content = self._generate_readme(products, successful_downloads)
                zip_file.writestr('README.txt', readme_content.encode('utf-8'))

            zip_buffer.seek(0)
            return zip_buffer

        except Exception as e:
            print(f"❌ Критическая ошибка при создании архива: {e}")
            import traceback
            traceback.print_exc()
            return await self._create_fallback_zip(products)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def _generate_readme(self, products: list, image_count: int) -> str:
        """Генерирует README файл"""
        return f"""Avito Export Archive
    Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    Total products: {len(products)}
    Total images: {image_count}

    Содержимое:
    - avito.xml - файл с объявлениями в формате Avito
    - 1.jpg, 2.jpg... - фотографии товаров

    Инструкция:
    1. Загрузите весь архив в личном кабинете Avito
    2. Система автоматически свяжет изображения с объявлениями
    3. Проверьте результат публикации

    Убедитесь, что все изображения имеют правильные форматы (JPEG, PNG)."""


    def _is_url(self, file_reference: str) -> bool:
            """Проверяет, является ли строка URL"""
            return file_reference.startswith(('http://', 'https://'))

    async def _create_fallback_zip(self, products: list) -> BytesIO:
        """Создает архив только с XML (резервный вариант)"""
        zip_buffer = BytesIO()

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Генерируем XML без images_map
            xml_content = self.generate_xml_content(products)
            zip_file.writestr('avito.xml', xml_content.encode('utf-8'))

            error_info = f"""ВНИМАНИЕ: Изображения не были добавлены в архив из-за ошибки.

    Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    Total products: {len(products)}

    Причина: Ошибка при обработке изображений
    Рекомендация: Проверьте доступность URL изображений"""

            zip_file.writestr('ERROR_INFO.txt', error_info.encode('utf-8'))

        zip_buffer.seek(0)
        return zip_buffer

    # bot/services/BaseXMLGenerator.py
    def _add_common_elements(self, ad: ET.Element, product: dict, city: str, ad_number: int = 1,
                             metro_station: str = None):
        """Добавление общих элементов"""
        # Id
        product_id = product.get('product_id', 'unknown')
        ET.SubElement(ad, "Id").text = f"{product_id}_{ad_number}" if ad_number > 1 else product_id

        # DateBegin (если указана)
        start_date = product.get('start_date')
        if start_date:
            if isinstance(start_date, str):
                ET.SubElement(ad, "DateBegin").text = start_date
            else:
                ET.SubElement(ad, "DateBegin").text = start_date.strftime('%d.%m.%Y %H:%M')

        # ListingFee (по умолчанию Package)
        ET.SubElement(ad, "ListingFee").text = "Package"

        # AdStatus (по умолчанию Free)
        ET.SubElement(ad, "AdStatus").text = "Free"

        # ContactPhone
        contact_phone = product.get('contact_phone', '')
        if contact_phone:
            ET.SubElement(ad, "ContactPhone").text = contact_phone

        # Address
        address = self._generate_address(city, ad_number, metro_station)
        ET.SubElement(ad, "Address").text = address

        # Title (ограничение 50 символов)
        title = product.get('title', 'Без названия')
        if len(title) > 50:
            title = title[:47] + "..."
        ET.SubElement(ad, "Title").text = title

        # Description (ограничение 7500 символов)
        description = product.get('description', '')
        if len(description) > 7500:
            description = description[:7497] + "..."
        if description:
            desc_elem = ET.SubElement(ad, "Description")
            desc_elem.text = description

        # Price
        price = self._get_product_price(product)
        if price > 0:
            ET.SubElement(ad, "Price").text = str(price)

        # ContactMethod
        contact_method = product.get('contact_method', 'both')
        contact_methods = {
            'both': 'По телефону и в сообщениях',
            'phone': 'По телефону',
            'message': 'В сообщениях'
        }
        ET.SubElement(ad, "ContactMethod").text = contact_methods.get(contact_method, 'По телефону и в сообщениях')

        # InternetCalls (по умолчанию Нет)
        ET.SubElement(ad, "InternetCalls").text = "Нет"

        # Delivery - ВЫЗЫВАЕМ МЕТОД КОРРЕКТНО
        avito_delivery = product.get('avito_delivery', False)
        if avito_delivery:
            self._add_delivery_to_ad(ad, product)

        # Condition
        condition = product.get('condition', '')
        if condition:
            condition_names = {
                "new_with_tag": "Новое с биркой",
                "excellent": "Отличное",
                "good": "Хорошее",
                "satisfactory": "Удовлетворительное"
            }
            ET.SubElement(ad, "Condition").text = condition_names.get(condition, condition)

        # AdType
        sale_type = product.get('sale_type', '')
        if sale_type:
            sale_type_names = {
                "manufacturer": "Товар от производителя",
                "resale": "Товар приобретен на продажу",
                "personal": "Частное лицо"
            }
            ET.SubElement(ad, "AdType").text = sale_type_names.get(sale_type, "Товар приобретен на продажу")


    def _add_images(self, ad: ET.Element, product: dict):
        """Старый метод - теперь используем _add_images_to_ad"""
        print("⚠️ Используется старый метод _add_images, рекомендуется обновить логику")
        all_images = product.get('all_images', [])
        if all_images:
            images_elem = ET.SubElement(ad, "Images")
            # Просто добавляем первые 10 изображений как 1.jpg, 2.jpg и т.д.
            for i in range(min(10, len(all_images))):
                ET.SubElement(images_elem, "Image", name=f"{i + 1}.jpg")

    def _get_product_price(self, product: dict) -> int:
        """Получение цены товара"""
        price_type = product.get('price_type', 'none')

        if price_type == 'fixed' and product.get('price'):
            return product['price']
        elif price_type == 'range' and product.get('price_min') and product.get('price_max'):
            return random.randint(product['price_min'], product['price_max'])
        else:
            return 0

    def _generate_address(self, city: str, ad_number: int = 1, metro_station: str = None) -> str:
        """Генерация адреса"""
        streets = [
            "ул. Ленина", "ул. Центральная", "ул. Советская", "ул. Мира",
            "ул. Молодежная", "ул. Школьная", "ул. Садовая", "ул. Лесная",
            "пр. Победы", "пр. Мира", "бульвар Свободы", "пер. Почтовый"
        ]

        street = random.choice(streets)
        building = random.randint(1, 100)

        if metro_station:
            return f"{city}, {street}, д. {building} (м. {metro_station})"
        elif ad_number > 1:
            return f"{city}, {street}, д. {building}, кв. {ad_number}"
        else:
            return f"{city}, {street}, д. {building}"

    def _extract_category_levels(self, product: dict) -> tuple:
        """
        Извлекает уровни категории из продукта
        Возвращает: (first_level, second_level, third_level)
        """
        category_id = product.get('category')
        category_name = product.get('category_name', '')

        print(f"📦 Извлечение уровней категории:")
        print(f"   ID: {category_id}")
        print(f"   Название: {category_name}")

        # Пробуем сначала по ID
        if category_id:
            first_level, second_level, third_level = CategoryService.get_category_levels(category_id)
            if first_level:  # Если нашли по ID
                print(f"✅ Используем уровни из ID")
                return first_level, second_level, third_level

        # Если не нашли по ID или ID пустой, используем название
        if category_name:
            print(f"✅ Используем уровни из названия")
            return CategoryService.get_category_levels_from_name(category_name)

        print(f"❌ Не удалось извлечь уровни категории")
        return "", "", ""

    def _get_apparel_value(self, second_level: str) -> str:
        """Возвращает точное название для Apparel"""
        return second_level if second_level else "Другое"

    def _get_dresstype_value(self, third_level: str) -> str:
        """Возвращает точное название для DressType"""
        return third_level

    def _add_size_to_common(self, ad: ET.Element, product: dict):
        """Добавляет тег <Size> с размером"""
        # Пробуем разные поля с размером
        size_fields = ['clothing_size', 'size', 'shoe_size']

        for field in size_fields:
            size_value = product.get(field, '')
            if size_value:
                print(f"✅ Добавляем размер в тег <Size> из поля '{field}': {size_value}")
                ET.SubElement(ad, "Size").text = size_value
                return

        print("❌ Размер не найден для тега <Size>")

    def _get_product_images_for_archive(self, product: dict) -> list:
        """Получает все изображения товара для добавления в архив"""
        all_images = product.get('all_images', [])
        return all_images

    def _get_images_for_ad(self, product: dict, ad_number: int, images_map: dict) -> list:
        """
        Получает список изображений для конкретного объявления
        """
        all_images = product.get('all_images', [])
        shuffle_images = product.get('shuffle_images', False)

        if not all_images:
            return []

        # Создаем копию списка изображений
        images_list = all_images.copy()

        # Перемешиваем если нужно
        if shuffle_images:
            import random
            random.shuffle(images_list)
            print(f"   🔀 Изображения перемешаны для объявления {ad_number}")

        # Ограничиваем количество изображений (максимум 10)
        images_list = images_list[:10]

        print(f"   📋 Для объявления {ad_number}: {len(images_list)} изображений")

        return images_list

    def _add_images_to_ad(self, ad: ET.Element, product: dict, ad_number: int, images_map: dict):
        """Добавляет изображения в объявление с правильными именами файлов"""
        images_for_ad = self._get_images_for_ad(product, ad_number, images_map)

        if not images_for_ad:
            print(f"   ⚠️ Нет изображений для объявления {ad_number}")
            return

        images_elem = ET.SubElement(ad, "Images")

        for i, img_url in enumerate(images_for_ad, 1):
            if img_url in images_map:
                filename = images_map[img_url]
                ET.SubElement(images_elem, "Image", name=filename)
                print(f"   ✅ Добавлено изображение {i}: {filename}")
            else:
                print(f"   ❌ Изображение не найдено в архиве: {img_url[:50]}...")

