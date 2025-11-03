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


class BaseXMLGenerator(ABC):
    """Базовый класс для генерации XML"""

    def __init__(self, image_service=None):
        self.format_version = "3"
        self.target = "Avito.ru"
        self.image_service = image_service

    @abstractmethod
    def generate_ad(self, product: dict, city: str, ad_number: int = 1, metro_station: str = None) -> ET.Element:
        """Генерация элемента объявления"""
        pass

    def generate_xml_content(self, products: list) -> str:
        """Генерация XML контента (без архива)"""
        root = ET.Element("Ads",
                          formatVersion=self.format_version,
                          target=self.target)

        ad_count = 0

        for product in products:
            # Получаем города для размещения
            cities = product.get('cities', [])
            quantity = product.get('quantity', 1)
            placement_method = product.get('placement_method', 'exact_cities')

            # Создаем объявления в зависимости от метода размещения
            if placement_method == 'multiple_in_city' and cities:
                # Мультиразмещение в одном городе
                for i in range(quantity):
                    ad = self.generate_ad(product, cities[0], i + 1)
                    root.append(ad)
                    ad_count += 1

            elif placement_method == 'by_quantity' and cities:
                # Размещение по количеству в разных городах
                for i in range(min(quantity, len(cities))):
                    city = cities[i] if i < len(cities) else cities[0]
                    ad = self.generate_ad(product, city, i + 1)
                    root.append(ad)
                    ad_count += 1

            elif placement_method == 'metro' and product.get('selected_metro_stations'):
                # Размещение по станциям метро
                metro_stations = product.get('selected_metro_stations', [])
                metro_city = product.get('metro_city', 'Москва')

                for i, station in enumerate(metro_stations[:quantity]):
                    ad = self.generate_ad(product, metro_city, i + 1, station)
                    root.append(ad)
                    ad_count += 1

            else:
                # Обычное размещение по городам
                for i, city in enumerate(cities[:quantity]):
                    ad = self.generate_ad(product, city, i + 1)
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
                    # Генерируем XML
                    xml_content = self.generate_xml_content(products)
                    zip_file.writestr('avito.xml', xml_content.encode('utf-8'))

                    # Собираем все уникальные изображения из всех товаров
                    all_image_refs = []
                    image_product_map = {}

                    for product in products:
                        images = product.get('all_images', [])
                        shuffle = product.get('shuffle_images', False)

                        if shuffle:
                            random.shuffle(images)

                        for img_ref in images:
                            if img_ref and img_ref not in image_product_map:
                                all_image_refs.append(img_ref)
                                image_product_map[img_ref] = product.get('product_id', 'unknown')

                    print(f"📸 Найдено {len(all_image_refs)} уникальных изображений для архива")

                    # Обрабатываем и добавляем изображения в архив
                    successful_downloads = 0
                    for i, image_ref in enumerate(all_image_refs[:50], 1):
                        try:
                            filename = f"{i}.jpg"
                            image_path = os.path.join(temp_dir, filename)

                            print(f"⬇️ Обрабатываем изображение {i}: {image_ref[:50]}...")

                            if self.image_service:
                                # Используем ImageService для скачивания
                                image_content = await self.image_service.process_image_for_export(image_ref)

                                if image_content:
                                    # Сохраняем изображение
                                    with open(image_path, 'wb') as f:
                                        f.write(image_content)

                                    zip_file.write(image_path, filename)
                                    successful_downloads += 1
                                    print(f"✅ Изображение {filename} успешно добавлено")
                                else:
                                    print(f"❌ Не удалось скачать изображение {image_ref}")
                            else:
                                # Старая логика для URL (для обратной совместимости)
                                if self._is_url(image_ref):
                                    response = requests.get(image_ref, timeout=30, stream=True)
                                    if response.status_code == 200:
                                        with open(image_path, 'wb') as f:
                                            for chunk in response.iter_content(chunk_size=8192):
                                                f.write(chunk)

                                        if self._is_valid_image(image_path):
                                            zip_file.write(image_path, filename)
                                            successful_downloads += 1
                                            print(f"✅ Изображение {filename} успешно добавлено")
                                        else:
                                            print(f"❌ Файл {filename} не является валидным изображением")
                                            os.remove(image_path)
                                    else:
                                        print(f"❌ Ошибка скачивания {image_ref}: статус {response.status_code}")
                                else:
                                    print(f"❌ Пропускаем не-URL изображение (вероятно file_id): {image_ref}")

                        except Exception as e:
                            print(f"❌ Ошибка при обработке изображения {image_ref}: {e}")
                            continue

                    print(f"✅ В архив добавлено {successful_downloads} изображений")

                    # Добавляем README файл
                    readme_content = self._generate_readme(products, successful_downloads)
                    zip_file.writestr('README.txt', readme_content.encode('utf-8'))

                zip_buffer.seek(0)
                return zip_buffer

            except Exception as e:
                print(f"❌ Критическая ошибка при создании архива: {e}")
                return self._create_fallback_zip(products)
            finally:
                shutil.rmtree(temp_dir, ignore_errors=True)

    def _is_url(self, file_reference: str) -> bool:
            """Проверяет, является ли строка URL"""
            return file_reference.startswith(('http://', 'https://'))

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

    def _create_fallback_zip(self, products: list) -> BytesIO:
        """Создает архив только с XML (резервный вариант)"""
        zip_buffer = BytesIO()

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            xml_content = self.generate_xml_content(products)
            zip_file.writestr('avito.xml', xml_content.encode('utf-8'))

            # Добавляем информацию об ошибке
            error_info = f"""ВНИМАНИЕ: Изображения не были добавлены в архив из-за ошибки.

    Причина: Не удалось скачать изображения с указанных URL.

    Рекомендации:
    1. Проверьте доступность изображений по URL
    2. Убедитесь, что изображения доступны без авторизации
    3. Попробуйте использовать прямые ссылки на изображения

    Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    Total products: {len(products)}"""

            zip_file.writestr('ERROR_IMAGES.txt', error_info.encode('utf-8'))

        zip_buffer.seek(0)
        return zip_buffer

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

        # Images
        self._add_images(ad, product)

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

        # Delivery
        if product.get('avito_delivery', False):
            delivery_elem = ET.SubElement(ad, "Delivery")
            ET.SubElement(delivery_elem, "Option").text = "ПВЗ"
            ET.SubElement(delivery_elem, "Option").text = "Курьер"

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
        """Добавление изображений с локальными именами"""
        all_images = product.get('all_images', [])
        shuffle = product.get('shuffle_images', False)

        if all_images:
            images_elem = ET.SubElement(ad, "Images")

            # Перемешиваем если нужно
            image_list = all_images.copy()
            if shuffle:
                random.shuffle(image_list)

            # Добавляем до 10 изображений с локальными именами
            for i, img_url in enumerate(image_list[:10], 1):
                # Используем локальные имена файлов (1.jpg, 2.jpg и т.д.)
                # Avito будет искать эти файлы в том же архиве
                ET.SubElement(images_elem, "Image", name=f"{i}.jpg")

            print(f"📷 Добавлено {min(len(image_list), 10)} изображений в XML")

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


