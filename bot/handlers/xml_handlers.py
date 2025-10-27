import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
import tempfile
import os
import random
from bot.database import db

router = Router()


def get_condition_name(condition_code: str) -> str:
    """Получение названия состояния товара"""
    conditions = {
        "new_with_tag": "Новое с биркой",
        "excellent": "Отличное",
        "good": "Хорошее",
        "satisfactory": "Удовлетворительное"
    }
    return conditions.get(condition_code, "Не указано")


def get_ad_type_name(ad_type: str) -> str:
    """Получение типа объявления"""
    ad_types = {
        "product": "Товар от производителя",
        "commercial": "Товар от коммерческого продавца",
        "part": "Запчасти"
    }
    return ad_types.get(ad_type, "Товар от производителя")


def get_delivery_methods(delivery_services: list) -> str:
    """Получение методов доставки"""
    delivery_names = {
        "pickup": "ПВЗ",
        "courier": "Курьер",
        "postamat": "Постамат",
        "own_courier": "Свой курьер",
        "sdek": "СДЭК",
        "business_lines": "Деловые Линии",
        "dpd": "DPD",
        "pek": "ПЭК",
        "russian_post": "Почта России",
        "sdek_courier": "СДЭК курьер",
        "self_pickup_online": "Самовывоз с онлайн-оплатой"
    }

    methods = [delivery_names.get(service, service) for service in delivery_services
               if service != "disabled"]
    return ", ".join(methods) if methods else "Не указано"


def get_delivery_discount_name(discount_code: str) -> str:
    """Получение названия скидки на доставку"""
    discounts = {
        "free": "Бесплатная доставка",
        "discount": "Скидка на доставку",
        "none": "Нет скидки"
    }
    return discounts.get(discount_code, "Не указано")


def generate_product_xml(products: list) -> str:
    """Генерация XML для списка товаров"""
    # Создаем корневой элемент
    root = ET.Element("Ads", formatVersion="3", target="Avito.ru")

    for product in products:
        # Создаем объявление для каждого города или множественные объявления
        cities = getattr(product, 'cities', [])
        quantity = getattr(product, 'quantity', 1)
        placement_method = getattr(product, 'placement_method', '')

        if placement_method == "multiple_in_city" and cities:
            # Создаем несколько объявлений в одном городе
            for i in range(quantity):
                ad = create_ad_element(product, cities[0] if cities else "", i + 1)
                root.append(ad)
        elif cities:
            # Создаем по одному объявлению в каждом городе
            for city in cities:
                ad = create_ad_element(product, city)
                root.append(ad)
        else:
            # Одно объявление без конкретного города
            ad = create_ad_element(product)
            root.append(ad)

    # Форматируем XML
    rough_string = ET.tostring(root, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    pretty_xml = reparsed.toprettyxml(indent="  ")

    return pretty_xml


def create_ad_element(product, city: str = "", ad_number: int = 1) -> ET.Element:
    """Создание элемента объявления"""
    ad = ET.Element("Ad")

    # Базовые поля
    ET.SubElement(ad, "Id").text = f"{product.product_id}_{ad_number}" if ad_number > 1 else product.product_id
    ET.SubElement(ad, "Title").text = product.title
    ET.SubElement(ad, "Description").text = product.description

    # Цена
    price = get_product_price(product)
    if price:
        ET.SubElement(ad, "Price").text = str(price)

    # Категория
    ET.SubElement(ad, "Category").text = product.category

    # Адрес
    address = generate_address(city, ad_number)
    ET.SubElement(ad, "Address").text = address

    # Контактный телефон
    ET.SubElement(ad, "ContactPhone").text = getattr(product, 'contact_phone', '')

    # Состояние товара
    condition = getattr(product, 'condition', '')
    if condition:
        ET.SubElement(ad, "Condition").text = condition

    # Тип объявления
    ad_type = getattr(product, 'sale_type', '')
    if ad_type == 'manufacturer':
        ET.SubElement(ad, "AdType").text = "Товар от производителя"
    elif ad_type == 'resale':
        ET.SubElement(ad, "AdType").text = "Товар приобретен на продажу"

    # Бренд
    brand = getattr(product, 'brand', '')
    if brand and brand != 'Не указан':
        ET.SubElement(ad, "GoodsType").text = brand

    # Размер
    size = getattr(product, 'size', '')
    if size:
        param = ET.SubElement(ad, "Param")
        ET.SubElement(param, "Name").text = "Размер"
        ET.SubElement(param, "Value").text = size

    # Доставка
    if getattr(product, 'avito_delivery', False):
        delivery = ET.SubElement(ad, "Delivery")
        delivery_services = getattr(product, 'delivery_services', [])

        for service in delivery_services:
            if service != "disabled":
                method = ET.SubElement(delivery, "Method")
                method.text = service

        # Скидка на доставку
        discount = getattr(product, 'delivery_discount', 'none')
        if discount != "none":
            discount_elem = ET.SubElement(delivery, "Discount")
            discount_elem.text = discount

    # Изображения
    images = getattr(product, 'all_images', getattr(product, 'images', []))
    if images:
        images_element = ET.SubElement(ad, "Images")
        for image_url in images[:10]:  # Авито принимает до 10 изображений
            image_elem = ET.SubElement(images_element, "Image")
            image_elem.set("url", image_url)

    # Мультиобъявление
    if getattr(product, 'multioffer', False):
        ET.SubElement(ad, "MultiOffer").text = "true"

    # Дополнительные параметры
    add_custom_params(ad, product)

    return ad


def get_product_price(product) -> int:
    """Получение цены товара с учетом типа цены"""
    price_type = getattr(product, 'price_type', 'none')

    if price_type == 'fixed':
        return getattr(product, 'price', 0)
    elif price_type == 'range':
        price_min = getattr(product, 'price_min', 0)
        price_max = getattr(product, 'price_max', 0)
        if price_min and price_max and price_min < price_max:
            return random.randint(price_min, price_max)
        return price_min
    else:
        return 0  # Без цены


def generate_address(city: str, ad_number: int) -> str:
    """Генерация адреса"""
    if not city:
        return "Россия"

    # Случайные улицы для генерации разных адресов
    streets = [
        "ул. Ленина", "ул. Центральная", "ул. Советская", "ул. Мира",
        "ул. Молодежная", "ул. Школьная", "ул. Садовая", "ул. Лесная",
        "пр. Победы", "пр. Мира", "бульвар Свободы", "пер. Почтовый"
    ]

    street = random.choice(streets)
    building = random.randint(1, 100)

    if ad_number > 1:
        # Для множественных объявлений добавляем номер квартиры
        apartment = ad_number
        return f"{city}, {street}, д. {building}, кв. {apartment}"
    else:
        return f"{city}, {street}, д. {building}"


def add_custom_params(ad: ET.Element, product):
    """Добавление пользовательских параметров"""
    # Состояние товара (текстовое представление)
    condition = getattr(product, 'condition', '')
    if condition:
        param = ET.SubElement(ad, "Param")
        ET.SubElement(param, "Name").text = "Состояние"
        ET.SubElement(param, "Value").text = get_condition_name(condition)

    # Способ связи
    contact_method = getattr(product, 'contact_method', 'both')
    if contact_method:
        param = ET.SubElement(ad, "Param")
        ET.SubElement(param, "Name").text = "Способ связи"
        if contact_method == 'both':
            ET.SubElement(param, "Value").text = "По телефону и в сообщениях"
        elif contact_method == 'phone':
            ET.SubElement(param, "Value").text = "По телефону"
        elif contact_method == 'message':
            ET.SubElement(param, "Value").text = "В сообщениях"

    # Информация о доставке
    if getattr(product, 'avito_delivery', False):
        delivery_services = getattr(product, 'delivery_services', [])
        if delivery_services:
            param = ET.SubElement(ad, "Param")
            ET.SubElement(param, "Name").text = "Способы доставки"
            ET.SubElement(param, "Value").text = get_delivery_methods(delivery_services)

        discount = getattr(product, 'delivery_discount', 'none')
        param = ET.SubElement(ad, "Param")
        ET.SubElement(param, "Name").text = "Скидка на доставку"
        ET.SubElement(param, "Value").text = get_delivery_discount_name(discount)


@router.message(Command("generate_xml"))
async def generate_xml_command(message: Message):
    """Генерация XML файла"""
    user_id = message.from_user.id
    products = await db.get_user_products(user_id)

    if not products:
        await message.answer("У вас нет товаров для генерации XML. Используйте /new_product чтобы добавить товар.")
        return

    try:
        # Генерируем XML
        xml_content = generate_product_xml(products)

        # Создаем временный файл
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False, encoding='utf-8') as f:
            f.write(xml_content)
            temp_filename = f.name

        # Статистика
        total_ads = 0
        for product in products:
            cities = getattr(product, 'cities', [])
            quantity = getattr(product, 'quantity', 1)
            placement_method = getattr(product, 'placement_method', '')

            if placement_method == "multiple_in_city" and cities:
                total_ads += quantity
            elif cities:
                total_ads += len(cities)
            else:
                total_ads += 1

        # Отправляем файл пользователю
        with open(temp_filename, 'rb') as f:
            await message.answer_document(
                document=f,
                filename=f"avito_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xml",
                caption=(
                    f"✅ XML файл для загрузки на Авито готов!\n\n"
                    f"📊 Статистика:\n"
                    f"• Товаров: {len(products)}\n"
                    f"• Объявлений: {total_ads}\n"
                    f"• Файл готов к загрузке в личном кабинете Авито\n\n"
                    f"💡 Загрузите этот файл в разделе автозагрузки объявлений Авито."
                )
            )

        # Удаляем временный файл
        os.unlink(temp_filename)

    except Exception as e:
        print(f"Error generating XML: {e}")
        await message.answer("Произошла ошибка при генерации XML файла. Попробуйте еще раз.")


@router.message(Command("my_products"))
async def my_products_command(message: Message):
    """Показать все товары пользователя"""
    user_id = message.from_user.id
    products = await db.get_user_products(user_id)

    if not products:
        await message.answer("У вас нет добавленных товаров. Используйте /new_product чтобы добавить товар.")
        return

    text = f"📦 Ваши товары ({len(products)}):\n\n"

    for i, product in enumerate(products, 1):
        cities = getattr(product, 'cities', [])
        quantity = getattr(product, 'quantity', 1)
        placement_method = getattr(product, 'placement_method', '')

        # Подсчет количества объявлений
        if placement_method == "multiple_in_city" and cities:
            ads_count = quantity
            location_info = f"{cities[0]} ({quantity} объявлений)"
        elif cities:
            ads_count = len(cities)
            location_info = f"{len(cities)} городов"
        else:
            ads_count = 1
            location_info = "без привязки к городу"

        text += f"{i}. {product.title}\n"
        text += f"   💰 Цена: {get_product_price(product) or 'Не указана'} руб.\n"
        text += f"   🏷️ Бренд: {getattr(product, 'brand', 'Не указан')}\n"
        text += f"   📍 Размещение: {location_info}\n"
        text += f"   🖼️ Фото: {getattr(product, 'total_images', 0)} шт.\n"
        text += "   ─────────────────────\n"

    text += "\nИспользуйте команды:\n"
    text += "/delete_product [номер] - удалить товар\n"
    text += "/generate_xml - создать XML файл для загрузки на Авито"

    await message.answer(text)


@router.message(Command("delete_product"))
async def delete_product_command(message: Message):
    """Удаление товара"""
    user_id = message.from_user.id
    args = message.text.split()[1:] if len(message.text.split()) > 1 else []

    if not args:
        await message.answer("Укажите номер товара для удаления: /delete_product [номер]")
        return

    try:
        index = int(args[0]) - 1
        success = await db.delete_product(user_id, index)
        if success:
            await message.answer("Товар успешно удален.")
        else:
            await message.answer("Неверный номер товара.")
    except ValueError:
        await message.answer("Номер должен быть числом.")