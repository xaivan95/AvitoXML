from pydoc import html

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove, KeyboardButton, ReplyKeyboardMarkup
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
import re
import random
import uuid
from datetime import datetime
from bot.calendar import ProductCalendar, CalendarCallback
from bot.database import db
from bot.handlers.metro_data import get_metro_stations, get_metro_cities
from bot.handlers.product_parameters import is_bag_category, get_bag_parameters
from bot.states import ProductStates
import config
import xml.etree.ElementTree as ET
from typing import List, Dict

from нф import validate_city_nominatim

# Категории, требующие размер
SIZE_CATEGORIES = [
    "Мужская обувь", "Женская обувь", "Мужская одежда", "Женская одежда",
    "Брюки", "Джинсы", "Шорты", "Пиджаки и костюмы", "Рубашки", "Платья", "Юбки"
]


async def ask_quantity_from_xml(message: Message, user_name: str = ""):
    """Запрос количества объявлений для метода из XML"""
    cities = load_cities_from_xml()
    total_cities = len(cities)

    # Показываем примеры городов
    sample_cities = ", ".join([city['name'] for city in cities[:5]])

    greeting = f"{user_name}, " if user_name else ""
    await message.answer(
        f"{greeting}введите количество объявлений (максимум {total_cities}):\n\n"
        f"🏙️ Будут использованы города из базы данных\n"
        f"📊 Всего доступно городов: {total_cities}\n"
        f"📍 Пример: {sample_cities}...\n"
        f"🎯 Будут выбраны города с наибольшим населением"
    )


def load_cities_from_xml() -> List[Dict]:
    """Загрузка городов из XML файла с обработкой ошибок"""
    try:
        tree = ET.parse('cities.xml')
        root = tree.getroot()

        cities = []
        for city_elem in root.findall('city'):
            try:
                name_elem = city_elem.find('name')
                population_elem = city_elem.find('population')
                region_elem = city_elem.find('region')

                if name_elem is not None and name_elem.text:
                    city_data = {
                        'name': name_elem.text.strip(),
                        'population': int(
                            population_elem.text) if population_elem is not None and population_elem.text else 0,
                        'region': region_elem.text if region_elem is not None else ''
                    }
                    cities.append(city_data)

            except (ValueError, AttributeError) as e:
                print(f"Error parsing city element: {e}")
                continue

        # Сортируем по населению (от большего к меньшему)
        cities.sort(key=lambda x: x['population'], reverse=True)
        return cities

    except Exception as e:
        print(f"Error loading cities XML: {e}")
        return get_default_cities()


def get_default_cities() -> List[Dict]:
    """Резервный список городов"""
    return [
        {'name': 'Москва', 'population': 12678079, 'region': 'Москва'},
        {'name': 'Санкт-Петербург', 'population': 5398064, 'region': 'Санкт-Петербург'},
        {'name': 'Новосибирск', 'population': 1625631, 'region': 'Новосибирская область'},
        {'name': 'Екатеринбург', 'population': 1493749, 'region': 'Свердловская область'},
        {'name': 'Нижний Новгород', 'population': 1244254, 'region': 'Нижегородская область'},
        {'name': 'Казань', 'population': 1257391, 'region': 'Татарстан'},
        {'name': 'Челябинск', 'population': 1187965, 'region': 'Челябинская область'},
        {'name': 'Омск', 'population': 1125695, 'region': 'Омская область'},
        {'name': 'Самара', 'population': 1144759, 'region': 'Самарская область'},
        {'name': 'Ростов-на-Дону', 'population': 1137704, 'region': 'Ростовская область'}
    ]


def get_default_cities() -> List[Dict]:
    """Резервный список городов"""
    return [
        {'name': 'Москва', 'population': 12678079, 'region': 'Москва'},
        {'name': 'Санкт-Петербург', 'population': 5398064, 'region': 'Санкт-Петербург'},
        {'name': 'Новосибирск', 'population': 1625631, 'region': 'Новосибирская область'},
        # ... добавьте другие города по необходимости
    ]


def get_cities_with_metro() -> List[Dict]:
    """Города с метро"""
    metro_cities = ['Москва', 'Санкт-Петербург', 'Нижний Новгород', 'Новосибирск',
                    'Самара', 'Екатеринбург', 'Казань', 'Волгоград']

    all_cities = load_cities_from_xml()
    return [city for city in all_cities if city['name'] in metro_cities]
# Добавьте новые вспомогательные функции
async def ask_brand(message: Message, user_name: str = ""):
    """Запрос бренда товара"""
    brands = load_brands()

    builder = InlineKeyboardBuilder()

    # Показываем первые 10 брендов + кнопку "Показать еще"
    for brand in brands[:10]:
        builder.button(text=brand, callback_data=f"brand_{brand}")

    builder.button(text="📋 Показать все бренды", callback_data="brand_show_all")
    builder.button(text="✏️ Ввести вручную", callback_data="brand_custom")

    builder.adjust(1)

    greeting = f"{user_name}, " if user_name else ""
    await message.answer(
        f"{greeting}выберите бренд товара:",
        reply_markup=builder.as_markup()
    )


async def ask_city_input(message: Message, user_name: str = ""):
    """Запрос ввода города по одному"""
    greeting = f"{user_name}, " if user_name else ""

    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="✅ Завершить ввод городов")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

    await message.answer(
        f"{greeting}введите название города:\n\n"
        "🏙️ Город будет проверен и предложен для подтверждения\n"
        "📝 Можно вводить города по одному\n"
        "✅ Нажмите кнопку ниже чтобы завершить",
        reply_markup=keyboard
    )

async def ask_size(message: Message, user_name: str = ""):
    """Запрос размера товара"""
    builder = InlineKeyboardBuilder()

    # Размеры одежды
    clothing_sizes = ["XS", "S", "M", "L", "XL", "XXL", "XXXL", "46", "48", "50", "52", "54", "56", "58"]
    # Размеры обуви
    shoe_sizes = ["35", "36", "37", "38", "39", "40", "41", "42", "43", "44", "45", "46"]

    for size in clothing_sizes + shoe_sizes:
        builder.button(text=size, callback_data=f"size_{size}")

    builder.button(text="✏️ Ввести другой размер", callback_data="size_custom")
    builder.button(text="⏩ Пропустить", callback_data="size_skip")

    builder.adjust(4)

    greeting = f"{user_name}, " if user_name else ""
    await message.answer(
        f"{greeting}выберите размер товара:",
        reply_markup=builder.as_markup()
    )


async def ask_condition(message: Message, user_name: str = ""):
    """Запрос состояния товара"""
    builder = InlineKeyboardBuilder()

    conditions = [
        ("🆕 Новое с биркой", "new_with_tag"),
        ("⭐ Отличное", "excellent"),
        ("👍 Хорошее", "good"),
        ("✅ Удовлетворительное", "satisfactory")
    ]

    for condition_name, condition_code in conditions:
        builder.button(text=condition_name, callback_data=f"condition_{condition_code}")

    builder.adjust(1)

    greeting = f"{user_name}, " if user_name else ""
    await message.answer(
        f"{greeting}выберите состояние товара:",
        reply_markup=builder.as_markup()
    )


async def ask_sale_type(message: Message, user_name: str = ""):
    """Запрос типа продажи"""
    builder = InlineKeyboardBuilder()

    sale_types = [
        ("🛒 Товар приобретен на продажу", "resale"),
        ("🏭 Товар от производителя", "manufacturer"),
        ("👤 Продаю своё", "personal")  # Добавляем новый тип
    ]

    for sale_name, sale_code in sale_types:
        builder.button(text=sale_name, callback_data=f"saletype_{sale_code}")

    builder.adjust(1)

    greeting = f"{user_name}, " if user_name else ""
    await message.answer(
        f"{greeting}выберите тип продажи:",
        reply_markup=builder.as_markup()
    )


async def ask_placement_type(message: Message, user_name: str = ""):
    """Запрос типа размещения"""
    builder = InlineKeyboardBuilder()

    placement_types = [
        ("🏙️ По городам", "cities"),
        ("🚇 По станциям метро", "metro")
    ]

    for placement_name, placement_code in placement_types:
        builder.button(text=placement_name, callback_data=f"placement_{placement_code}")

    builder.adjust(1)

    greeting = f"{user_name}, " if user_name else ""
    await message.answer(
        f"{greeting}выберите вариант размещения объявлений:",
        reply_markup=builder.as_markup()
    )


async def ask_placement_method(message: Message, user_name: str = ""):
    """Запрос метода размещения"""
    builder = InlineKeyboardBuilder()

    placement_methods = [
        ("📍 Указать точные города", "exact_cities"),
        ("📊 По количеству объявлений", "by_quantity"),
        ("🏢 Несколько объявлений в городе", "multiple_in_city")
    ]

    for method_name, method_code in placement_methods:
        builder.button(text=method_name, callback_data=f"method_{method_code}")

    builder.adjust(1)

    greeting = f"{user_name}, " if user_name else ""
    await message.answer(
        f"{greeting}выберите вариант размещения:",
        reply_markup=builder.as_markup()
    )



async def ask_cities(message: Message, user_name: str = ""):
    """Запрос городов"""
    greeting = f"{user_name}, " if user_name else ""
    await message.answer(
        f"{greeting}введите названия городов через запятую:\n\n"
        "Пример: Москва, Санкт-Петербург, Новосибирск"
    )


async def ask_quantity(message: Message, user_name: str = ""):
    """Запрос количества объявлений"""
    greeting = f"{user_name}, " if user_name else ""
    await message.answer(
        f"{greeting}введите количество объявлений для размещения:"
    )
router = Router()

# Словари для временного хранения альбомов
temp_main_albums = {}
temp_additional_albums = {}


def generate_guid() -> str:
    """Генерация уникального GUID для товара"""
    return str(uuid.uuid4())


async def show_main_categories(message: Message, user_name: str = ""):
    """Показать основные категории"""
    builder = InlineKeyboardBuilder()

    for cat_id, cat_data in config.AVITO_CATEGORIES.items():
        builder.button(text=cat_data["name"], callback_data=f"cat_{cat_id}")

    builder.adjust(1)

    greeting = f"{user_name}, " if user_name else ""
    await message.answer(
        f"{greeting}🎯 Начинаем добавление нового товара!\n\n"
        "Выберите основную категорию:",
        reply_markup=builder.as_markup()
    )


async def show_subcategories(message: Message, category_id: str, user_name: str = ""):
    """Показать подкатегории для выбранной категории"""
    category_data = config.AVITO_CATEGORIES.get(category_id)
    if not category_data:
        await message.answer("Ошибка: категория не найдена")
        return

    subcategories = category_data.get("subcategories", {})
    if not subcategories:
        await message.answer("В этой категории нет подкатегорий")
        return

    builder = InlineKeyboardBuilder()

    for subcat_id, subcat_name in subcategories.items():
        builder.button(text=subcat_name, callback_data=f"sub_{subcat_id}")

    builder.button(text="🔙 Назад к категориям", callback_data="back_categories")
    builder.adjust(1)

    greeting = f"{user_name}, " if user_name else ""
    await message.answer(
        f"{greeting}выберите подкатегорию для {category_data['name']}:",
        reply_markup=builder.as_markup()
    )


async def show_price_type_options(message: Message, user_name: str = ""):
    """Показать варианты указания цены"""
    builder = InlineKeyboardBuilder()

    builder.button(text="💰 Фиксированная цена", callback_data="price_fixed")
    builder.button(text="📊 Диапазон цен", callback_data="price_range")
    builder.button(text="⏩ Пропустить", callback_data="price_skip")

    builder.adjust(1)

    greeting = f"{user_name}, " if user_name else ""
    await message.answer(
        f"{greeting}укажите стоимость:\n\n"
        "1) 💰 Фиксированная цена (например 1234) - всем объявлениям в файле будет присвоена одна цена\n"
        "2) 📊 Диапазон цен (например 1200-1500) - каждому объявлению внутри файла будет присвоена случайная цена из указанного диапазона\n"
        "3) ⏩ Пропустить - цена указана не будет",
        reply_markup=builder.as_markup()
    )


async def show_contact_methods(message: Message, user_name: str = ""):
    """Показать варианты способов связи"""
    builder = InlineKeyboardBuilder()

    builder.button(text="📞 По телефону и в сообщении", callback_data="contact_both")
    builder.button(text="📞 По телефону", callback_data="contact_phone")
    builder.button(text="💬 В сообщении", callback_data="contact_message")

    builder.adjust(1)

    greeting = f"{user_name}, " if user_name else ""
    await message.answer(
        f"{greeting}выберите предпочтительный способ связи:",
        reply_markup=builder.as_markup()
    )


async def ask_additional_images(message: Message, state: FSMContext, user_name: str = ""):
    """Запрос дополнительных изображений"""
    greeting = f"{user_name}, " if user_name else ""

    # Получаем текущее количество основных фото через state
    data = await state.get_data()
    main_count = len(data.get('main_images', []))

    await message.answer(
        f"{greeting}теперь отправьте ДОПОЛНИТЕЛЬНЫЕ фотографии объявления.\n\n"
        f"📸 У вас уже {main_count} основных фото\n"
        "Вы можете отправлять:\n"
        "• 📷 По одному фото\n"
        "• 🖼️ Несколько фото одним сообщением (альбом)\n"
        "• 📤 Несколько сообщениями\n\n"
        "💡 Все фото будут сразу добавляться в счетчик\n\n"
        "После отправки всех дополнительных фото нажмите /finish_additional_images\n\n"
        "💡 Если дополнительных фото нет, просто нажмите /finish_additional_images"
    )

async def ask_shuffle_images(message: Message, state: FSMContext, user_name: str = ""):
    """Запрос о перемешивании фото"""
    builder = InlineKeyboardBuilder()

    builder.button(text="✅ Да, перемешать", callback_data="shuffle_yes")
    builder.button(text="❌ Нет, оставить как есть", callback_data="shuffle_no")

    builder.adjust(1)

    greeting = f"{user_name}, " if user_name else ""

    # Получаем данные состояния
    data = await state.get_data()

    main_count = len(data.get('main_images', []))
    additional_count = len(data.get('additional_images', []))
    total_count = main_count + additional_count

    await message.answer(
        f"{greeting}нужно ли перемешать фото?\n\n"
        f"📊 Статистика фото:\n"
        f"• Основные: {main_count}\n"
        f"• Дополнительные: {additional_count}\n"
        f"• Всего: {total_count}\n\n"
        "При перемешивании все фото будут расположены в случайном порядке.",
        reply_markup=builder.as_markup()
    )


async def ask_avito_delivery(message: Message, user_name: str = ""):
    """Запрос о подключении Авито доставки"""
    builder = InlineKeyboardBuilder()

    builder.button(text="✅ Да, подключить", callback_data="delivery_yes")
    builder.button(text="❌ Нет, не нужно", callback_data="delivery_no")

    builder.adjust(1)

    greeting = f"{user_name}, " if user_name else ""
    await message.answer(
        f"{greeting}нужно ли подключить Авито доставку?",
        reply_markup=builder.as_markup()
    )


async def ask_delivery_services(message: Message, state: FSMContext, user_name: str = ""):
    """Запрос выбора служб доставки"""
    builder = InlineKeyboardBuilder()

    delivery_services = [
        ("Выключена", "disabled"),
        ("ПВЗ", "pickup"),
        ("Курьер", "courier"),
        ("Постамат", "postamat"),
        ("Свой курьер", "own_courier"),
        ("Свой партнер СДЭК", "sdek"),
        ("Свой партнер Деловые Линии", "business_lines"),
        ("Свой партнер DPD", "dpd"),
        ("Свой партнер ПЭК", "pek"),
        ("Свой партнер Почта России", "russian_post"),
        ("Свой партнер СДЭК курьер", "sdek_courier"),
        ("Самовывоз с онлайн-оплатой", "self_pickup_online")
    ]

    # Получаем текущие выбранные службы
    data = await state.get_data()
    selected_services = data.get('delivery_services', [])

    for service_name, service_code in delivery_services:
        if service_code in selected_services:
            builder.button(text=f"✅ {service_name}", callback_data=f"service_{service_code}")
        else:
            builder.button(text=service_name, callback_data=f"service_{service_code}")

    builder.button(text="✅ Завершить выбор", callback_data=f"service_done")
    builder.adjust(1)

    selected_text = ", ".join([name for name, code in delivery_services if code in selected_services])

    greeting = f"{user_name}, " if user_name else ""
    await message.answer(
        f"{greeting}выберите службы доставки (можно выбрать несколько):\n\n"
        f"📦 Выбрано: {selected_text or 'ничего'}\n\n"
        "💡 Нажимайте на кнопки для выбора/отмены выбора. Рядом с выбранными появится галочка.\n"
        "Когда закончите выбор, нажмите '✅ Завершить выбор'",
        reply_markup=builder.as_markup()
    )


async def update_delivery_services_keyboard(message: Message, state: FSMContext, user_name: str = ""):
    """Обновление клавиатуры выбора служб доставки"""
    data = await state.get_data()
    selected_services = data.get('delivery_services', [])

    builder = InlineKeyboardBuilder()

    delivery_services = [
        ("Выключена", "disabled"),
        ("ПВЗ", "pickup"),
        ("Курьер", "courier"),
        ("Постамат", "postamat"),
        ("Свой курьер", "own_courier"),
        ("Свой партнер СДЭК", "sdek"),
        ("Свой партнер Деловые Линии", "business_lines"),
        ("Свой партнер DPD", "dpd"),
        ("Свой партнер ПЭК", "pek"),
        ("Свой партнер Почта России", "russian_post"),
        ("Свой партнер СДЭК курьер", "sdek_courier"),
        ("Самовывоз с онлайн-оплатой", "self_pickup_online")
    ]

    for service_name, service_code in delivery_services:
        if service_code in selected_services:
            builder.button(text=f"✅ {service_name}", callback_data=f"service_{service_code}")
        else:
            builder.button(text=service_name, callback_data=f"service_{service_code}")

    builder.button(text="✅ Завершить выбор", callback_data=f"service_done")
    builder.adjust(1)

    selected_text = ", ".join([name for name, code in delivery_services if code in selected_services])

    greeting = f"{user_name}, " if user_name else ""
    await message.edit_text(
        f"{greeting}выберите службы доставки (можно выбрать несколько):\n\n"
        f"📦 Выбрано: {selected_text or 'ничего'}\n\n"
        "💡 Нажимайте на кнопки для выбора/отмены выбора. Рядом с выбранными появится галочка.\n"
        "Когда закончите выбор, нажмите '✅ Завершить выбор'",
        reply_markup=builder.as_markup()
    )


async def ask_start_date(message: Message, user_name: str = ""):
    """Запрос даты старта продажи"""
    greeting = f"{user_name}, " if user_name else ""
    calendar = ProductCalendar()

    await message.answer(
        f"{greeting}выберите дату начала продажи:\n\n"
        "📅 Вы можете выбрать конкретную дату или пропустить этот шаг "
        "(в этом случае продажа начнется сразу после публикации).",
        reply_markup=await calendar.start_calendar()
    )


def load_brands() -> List[str]:
    """Загрузка брендов из XML файла с обработкой ошибок"""
    try:
        # Сначала пробуем стандартный парсинг
        return load_brands_standard()
    except Exception as e:
        print(f"Standard parsing failed: {e}")
        # Если не получается, используем fallback
        return load_brands_fallback()


def load_brands_standard() -> List[str]:
    """Стандартный парсинг XML"""
    try:
        tree = ET.parse('brands.xml')
        root = tree.getroot()

        brands = []

        # Пробуем разные структуры XML
        if root.tag == 'Brendy_fashion':
            for brand_elem in root.findall('brand'):
                brand_name = brand_elem.get('name')
                if brand_name:
                    brands.append(brand_name)
        else:
            # Ищем любые элементы brand
            for brand_elem in root.findall('.//brand'):
                brand_name = brand_elem.get('name')
                if brand_name:
                    brands.append(brand_name)
                elif brand_elem.text and brand_elem.text.strip():
                    brands.append(brand_elem.text.strip())

        return brands

    except ET.ParseError:
        # Если XML с ошибками, используем fallback
        raise Exception("XML parse error")


def load_brands_fallback() -> List[str]:
    """Альтернативный способ загрузки брендов через регулярные выражения"""
    try:
        with open('brands.xml', 'r', encoding='utf-8') as f:
            content = f.read()

        brands = []

        # Способ 1: Ищем name="значение"
        pattern1 = r'name="([^"]*)"'
        matches1 = re.findall(pattern1, content)
        brands.extend(matches1)

        # Способ 2: Ищем <brand>текст</brand>
        pattern2 = r'<brand[^>]*>([^<]+)</brand>'
        matches2 = re.findall(pattern2, content)
        brands.extend([match.strip() for match in matches2])

        # Способ 3: Ищем любые теги brand с атрибутами
        pattern3 = r'<brand\s+[^>]*name\s*=\s*["\']([^"\']*)["\']'
        matches3 = re.findall(pattern3, content)
        brands.extend(matches3)

        # Убираем дубликаты и пустые строки
        unique_brands = list(set([brand for brand in brands if brand.strip()]))

        print(f"Fallback loaded {len(unique_brands)} brands")
        return unique_brands

    except Exception as e:
        print(f"Fallback loading failed: {e}")
        # Возвращаем дефолтный список брендов
        return get_default_brands()


def get_default_brands() -> List[str]:
    """Возвращает список брендов по умолчанию"""
    return [
        "Nike", "Adidas", "Reebok", "Puma", "No name", "Другой бренд",
        "Zara", "H&M", "Uniqlo", "Gucci", "Louis Vuitton"
    ]


def is_valid_brand(brand: str) -> bool:
    """Проверка наличия бренда в базе (регистронезависимая)"""
    brands = load_brands()

    # Приводим к нижнему регистру для сравнения
    brand_lower = brand.lower().strip()

    for existing_brand in brands:
        if existing_brand.lower().strip() == brand_lower:
            return True

    return False


def search_brands(query: str) -> List[str]:
    """Поиск брендов по частичному совпадению"""
    brands = load_brands()
    query_lower = query.lower().strip()

    matches = []
    for brand in brands:
        if query_lower in brand.lower():
            matches.append(brand)

    return matches[:10]  # Ограничиваем количество результатов

async def ask_brand_manual(message: Message, user_name: str = ""):
    """Запрос бренда с ручным вводом и подсказками"""
    greeting = f"{user_name}, " if user_name else ""

    # Показываем несколько примеров брендов для справки
    sample_brands = load_brands()[:5]  # Первые 5 брендов как пример

    sample_text = "\n".join([f"• {brand}" for brand in sample_brands])

    await message.answer(
        f"{greeting}введите название бренда:\n\n"
        f"📋 Примеры брендов из базы:\n{sample_text}\n\n"
        "💡 Бренд будет проверен в базе данных. "
        "Если бренда нет в базе, вы сможете ввести его еще раз.\n"
        "🔍 Можно ввести часть названия для поиска."
    )


async def complete_product_creation(message: Message, state: FSMContext, user_name: str = ""):
    """Завершение создания товара и сохранение в базу"""
    try:
        data = await state.get_data()

        # Проверяем обязательные поля
        required_fields = ['title', 'description', 'category', 'contact_phone']
        missing_fields = [field for field in required_fields if not data.get(field)]

        if missing_fields:
            await message.answer(f"Ошибка: не заполнены обязательные поля: {', '.join(missing_fields)}")
            return

        # Формируем информацию о дате старта
        start_date_info = "сразу после публикации"
        if data.get('start_datetime'):
            start_date_info = data['start_datetime'].strftime('%d.%m.%Y %H:%M')
        elif data.get('start_date'):
            start_date_info = data['start_date'].strftime('%d.%m.%Y') + " (время не указано)"

        # Объединяем ВСЕ изображения (основные + дополнительные)
        main_images = data.get('main_images', [])
        additional_images = data.get('additional_images', [])
        all_images = main_images + additional_images

        # Перемешиваем если нужно
        if data.get('shuffle_images', False) and all_images:
            random.shuffle(all_images)

        # Обработка данных о размещении
        placement_method = data.get('placement_method', '')
        placement_type = data.get('placement_type', '')

        # Нормализуем данные о городах
        cities = data.get('cities', [])
        selected_cities = data.get('selected_cities', [])
        quantity = data.get('quantity', 1)

        # Если есть полные данные о городах, используем их
        if selected_cities and not cities:
            cities = [city['name'] for city in selected_cities]

        # Если cities - не список, преобразуем
        if cities and not isinstance(cities, list):
            cities = [cities]

        # Обработка данных о метро
        metro_data = {}
        if placement_method == "metro":
            metro_city = data.get('metro_city')
            metro_stations = data.get('selected_metro_stations', [])
            if metro_city and metro_stations:
                metro_data = {
                    'metro_city': metro_city,
                    'metro_stations': metro_stations,
                    'metro_quantity': quantity
                }
                # Убеждаемся что город добавлен в общий список
                if metro_city not in cities:
                    cities.append(metro_city)

        # Сохраняем товар в базу
        product_data = {
            'product_id': data.get('product_id'),
            'title': data.get('title'),
            'description': data.get('description'),
            'price': data.get('price'),
            'price_type': data.get('price_type', 'none'),
            'price_min': data.get('price_min'),
            'price_max': data.get('price_max'),
            'category': data.get('category'),
            'category_name': data.get('category_name', ''),
            'contact_phone': data.get('contact_phone'),
            'display_phone': data.get('display_phone', ''),
            'contact_method': data.get('contact_method', 'both'),
            'main_images': main_images,
            'additional_images': additional_images,
            'all_images': all_images,
            'total_images': len(all_images),
            'shuffle_images': data.get('shuffle_images', False),
            'avito_delivery': data.get('avito_delivery', False),
            'delivery_services': data.get('delivery_services', []),
            'delivery_discount': data.get('delivery_discount', 'none'),
            'multioffer': data.get('multioffer', False),
            'brand': data.get('brand', 'Не указан'),
            'size': data.get('size', ''),
            'condition': data.get('condition', ''),
            'sale_type': data.get('sale_type', ''),
            'placement_type': placement_type,
            'placement_method': placement_method,
            'cities': cities,
            'selected_cities': selected_cities,
            'quantity': quantity,
            # Данные о метро
            **metro_data,
            # Дата и время старта
            'start_date': data.get('start_date'),
            'start_time': data.get('start_time'),
            'start_datetime': data.get('start_datetime')
        }

        await db.add_product(message.from_user.id, product_data)

        await state.clear()
        await db.clear_user_state(message.from_user.id)

        # Статистика
        main_count = len(main_images)
        additional_count = len(additional_images)
        delivery_services = data.get('delivery_services', [])
        delivery_discount = data.get('delivery_discount', 'none')
        multioffer = data.get('multioffer', False)

        # Тексты для статистики
        delivery_text = "не подключена"
        if data.get('avito_delivery', False) and delivery_services:
            delivery_names = {
                "disabled": "Выключена",
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
            selected_names = [delivery_names.get(code, code) for code in delivery_services if code != "disabled"]
            delivery_text = ", ".join(selected_names) if selected_names else "не выбрано"

        discount_names = {
            "free": "🆓 Бесплатная доставка",
            "discount": "💰 Скидка на доставку",
            "none": "🚫 Нет скидки"
        }

        condition_names = {
            "new_with_tag": "🆕 Новое с биркой",
            "excellent": "⭐ Отличное",
            "good": "👍 Хорошее",
            "satisfactory": "✅ Удовлетворительное"
        }

        sale_type_names = {
            "resale": "🛒 Товар приобретен на продажу",
            "manufacturer": "🏭 Товар от производителя",
            "personal": "👤 Продаю своё"
        }

        contact_method_names = {
            "both": "📞 По телефону и в сообщении",
            "phone": "📞 По телефону",
            "message": "💬 В сообщении"
        }

        price_info = "Не указана"
        if data.get('price_type') == 'fixed' and data.get('price'):
            price_info = f"{data['price']} руб. (фиксированная)"
        elif data.get('price_type') == 'range' and data.get('price_min') and data.get('price_max'):
            price_info = f"{data['price_min']}-{data['price_max']} руб. (диапазон)"

        # Информация о размещении
        placement_info = "Не указано"
        if placement_method == "exact_cities" and cities:
            placement_info = f"По городам: {', '.join(cities)} ({len(cities)} городов)"
        elif placement_method == "by_quantity" and cities:
            placement_info = f"По количеству: {quantity} объявлений в {len(cities)} городах"
        elif placement_method == "multiple_in_city" and cities:
            placement_info = f"Мультиразмещение в {cities[0]}: {quantity} объявлений"
        elif placement_method == "metro" and metro_data:
            placement_info = f"По станциям метро: {metro_data['metro_city']}, {quantity} объявлений"
        elif placement_type == "cities":
            placement_info = "По городам (метод не выбран)"
        elif placement_type == "metro":
            placement_info = "По станциям метро (метод не выбран)"

        await message.answer(
            f"{user_name}, ✅ товар успешно добавлен!\n\n"
            f"📋 Статистика:\n"
            f"• Заголовок: {data['title'][:50]}...\n"
            f"• Описание: {len(data['description'])} символов\n"
            f"• Категория: {data.get('category_name', 'Не указана')}\n"
            f"• Цена: {price_info}\n"
            f"• Дата старта: {start_date_info}\n"
            f"• Бренд: {data.get('brand', 'Не указан')}\n"
            f"• Размер: {data.get('size', 'Не указан')}\n"
            f"• Состояние: {condition_names.get(data.get('condition', ''), 'Не указано')}\n"
            f"• Тип продажи: {sale_type_names.get(data.get('sale_type', ''), 'Не указан')}\n"
            f"• Способ связи: {contact_method_names.get(data.get('contact_method', 'both'), 'Не указан')}\n"
            f"• Телефон: {data.get('display_phone', 'Не указан')}\n"
            f"• Размещение: {placement_info}\n"
            f"• Основные фото: {main_count}\n"
            f"• Дополнительные фото: {additional_count}\n"
            f"• Всего фото: {len(all_images)}\n"
            f"• Перемешивание фото: {'✅ Да' if data.get('shuffle_images') else '❌ Нет'}\n"
            f"• Доставка: {delivery_text}\n"
            f"• Скидка на доставку: {discount_names.get(delivery_discount, 'Не указано')}\n"
            f"• Мультиобъявление: {'✅ Да' if multioffer else '❌ Нет'}\n\n"
            f"📊 Итог: создан товар с {len(all_images)} фото для {quantity} объявлений\n\n"
            f"Используйте команды:\n"
            f"/new_product - добавить новый товар\n"
            f"/my_products - посмотреть все товары\n"
            f"/generate_xml - создать XML файл для Avito"
        )

    except Exception as e:
        print(f"Error in complete_product_creation: {e}")
        await message.answer(
            "❌ Произошла ошибка при сохранении товара. Попробуйте еще раз.\n"
            "Если ошибка повторяется, используйте /new_product для начала заново."
        )


async def ask_start_time(message: Message, user_name: str = ""):
    """Запрос времени старта продажи"""
    greeting = f"{user_name}, " if user_name else ""

    builder = InlineKeyboardBuilder()

    # Популярные времена
    popular_times = [
        "09:00", "10:00", "11:00", "12:00",
        "13:00", "14:00", "15:00", "16:00",
        "17:00", "18:00", "19:00", "20:00"
    ]

    for time in popular_times:
        builder.button(text=time, callback_data=f"time_{time}")

    builder.button(text="✏️ Ввести вручную", callback_data="time_custom")
    builder.adjust(3)

    await message.answer(
        f"{greeting}выберите время начала продажи:\n\n"
        "⏰ Укажите время в формате ЧЧ:ММ (например, 14:30)\n"
        "Или выберите из популярных вариантов:",
        reply_markup=builder.as_markup()
    )

async def ask_phone_number(message: Message, user_name: str = ""):
        """Запрос номера телефона с кнопкой поделиться"""
        greeting = f"{user_name}, " if user_name else ""

        # Создаем клавиатуру с кнопкой "Поделиться номером"
        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="📞 Поделиться номером", request_contact=True)],
                [KeyboardButton(text="✏️ Ввести вручную")]
            ],
            resize_keyboard=True,
            one_time_keyboard=True
        )

        await message.answer(
            f"{greeting}укажите контактный номер телефона:\n\n"
            "Вы можете:\n"
            "• Нажать кнопку '📞 Поделиться номером' для автоматической отправки\n"
            "• Или ввести номер вручную в одном из форматов:\n"
            "  — +7 (495) 777-10-66\n"
            "  — 8 905 207 04 90\n"
            "  — 89052070490",
            reply_markup=keyboard
        )


async def ask_metro_city(message: Message, user_name: str = ""):
    """Запрос выбора города с метро"""
    metro_cities = get_metro_cities()

    if not metro_cities:
        await message.answer(
            "❌ В базе данных нет городов с метро.\n"
            "Пожалуйста, выберите другой тип размещения."
        )
        # Возвращаем к выбору типа размещения
        await ask_placement_type(message, user_name)
        return

    builder = InlineKeyboardBuilder()

    for city in metro_cities:
        stations_count = len(get_metro_stations(city))
        builder.button(
            text=f"🚇 {city} ({stations_count} станций)",
            callback_data=f"metro_city_{city}"
        )

    # Добавляем кнопку возврата
    builder.button(text="🔙 Назад к выбору типа", callback_data="back_to_placement_type")
    builder.adjust(1)

    greeting = f"{user_name}, " if user_name else ""
    await message.answer(
        f"{greeting}выберите город с метро:",
        reply_markup=builder.as_markup()
    )
# ========== ОСНОВНЫЕ ОБРАБОТЧИКИ ==========
@router.callback_query(F.data == "back_to_placement_type", StateFilter(ProductStates.waiting_for_metro_city))
async def back_to_placement_type(callback: CallbackQuery, state: FSMContext):
    """Возврат к выбору типа размещения из выбора города метро"""
    user_name = callback.from_user.first_name
    await state.set_state(ProductStates.waiting_for_placement_type)
    await callback.message.edit_text(f"{user_name}, возврат к выбору типа размещения.")
    await ask_placement_type(callback.message, user_name)


@router.callback_query(F.data.startswith("metro_city_"), StateFilter(ProductStates.waiting_for_metro_city))
async def process_metro_city(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора города с метро"""
    city_name = callback.data[11:]  # Убираем "metro_city_"

    stations = get_metro_stations(city_name)
    if not stations:
        await callback.answer("❌ В этом городе нет данных о станциях метро", show_alert=True)
        # Предлагаем выбрать другой город
        await ask_metro_city(callback.message, callback.from_user.first_name)
        return

    # Сохраняем данные о выбранном городе и станциях
    await state.update_data(
        metro_city=city_name,
        metro_stations=stations,
        cities=[city_name],  # Сохраняем город для общего списка
        placement_method="metro"  # Явно указываем метод
    )

    # Переходим к вводу количества объявлений
    await state.set_state(ProductStates.waiting_for_metro_quantity)

    user_name = callback.from_user.first_name

    # Показываем примеры станций
    sample_stations = ", ".join(stations[:5])

    await callback.message.edit_text(
        f"{user_name}, выбран город: 🚇 {city_name}\n\n"
        f"📍 Примеры станций: {sample_stations}...\n"
        f"📊 Всего станций: {len(stations)}\n\n"
        "Теперь введите количество объявлений:"
    )


async def ask_metro_quantity(message: Message, user_name: str = ""):
    """Запрос количества объявлений для метро с кнопкой возврата"""
    greeting = f"{user_name}, " if user_name else ""

    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Назад к выбору города", callback_data="back_to_metro_city")
    builder.adjust(1)

    await message.answer(
        f"{greeting}введите количество объявлений:\n\n"
        "🚇 Объявления будут распределены по станциям метро\n"
        "📍 Каждое объявление получит случайную станцию\n"
        "🏠 Адреса будут сгенерированы рядом со станциями",
        reply_markup=builder.as_markup()
    )

@router.callback_query(F.data == "back_to_metro_city", StateFilter(ProductStates.waiting_for_metro_quantity))
async def back_to_metro_city(callback: CallbackQuery, state: FSMContext):
    """Возврат к выбору города метро из ввода количества"""
    user_name = callback.from_user.first_name
    await state.set_state(ProductStates.waiting_for_metro_city)
    await callback.message.edit_text(f"{user_name}, возврат к выбору города.")
    await ask_metro_city(callback.message, user_name)

@router.message(StateFilter(ProductStates.waiting_for_metro_quantity))
async def process_metro_quantity(message: Message, state: FSMContext):
    """Обработка количества объявлений для метро"""
    try:
        quantity = int(message.text.strip())

        if quantity <= 0:
            await message.answer("Количество должно быть положительным числом. Введите количество:")
            return

        if quantity > 100:
            await message.answer("Максимальное количество: 100. Введите меньшее число:")
            return

        data = await state.get_data()
        city_name = data.get('metro_city')
        all_stations = data.get('metro_stations', [])

        # Выбираем случайные станции
        import random
        if quantity <= len(all_stations):
            selected_stations = random.sample(all_stations, quantity)
        else:
            # Если нужно больше объявлений чем станций, повторяем некоторые станции
            selected_stations = all_stations.copy()
            while len(selected_stations) < quantity:
                selected_stations.append(random.choice(all_stations))

        await state.update_data(
            quantity=quantity,
            selected_metro_stations=selected_stations,
            placement_method="metro"
        )

        user_name = message.from_user.first_name

        # Показываем несколько выбранных станций для примера
        sample_display = ", ".join(selected_stations[:3])
        if len(selected_stations) > 3:
            sample_display += f" и ещё {len(selected_stations) - 3}"

        await message.answer(
            f"{user_name}, ✅ настроено размещение по метро!\n\n"
            f"🏙️ Город: {city_name}\n"
            f"🚇 Использовано станций: {len(set(selected_stations))}\n"
            f"📊 Количество объявлений: {quantity}\n"
            f"📍 Примеры станций: {sample_display}\n\n"
            "🏠 Каждое объявление получит адрес рядом со станцией метро"
        )

        await state.set_state(ProductStates.waiting_for_start_date)
        await ask_start_date(message, user_name)

    except ValueError:
        await message.answer("Количество должно быть числом. Введите количество:")


# Создаем отдельный обработчик для мультиразмещения
@router.message(StateFilter(ProductStates.waiting_for_city_input))
async def handle_city_input(message: Message, state: FSMContext):
    """Общий обработчик ввода городов с учетом метода размещения"""
    data = await state.get_data()
    placement_method = data.get('placement_method')

    # Проверяем команду завершения
    if message.text == "✅ Завершить ввод городов":
        await finish_city_input(message, state)
        return

    if placement_method == "multiple_in_city":
        await process_single_city_for_multiple(message, state)
    else:
        await process_city_input(message, state)


async def process_single_city_for_multiple(message: Message, state: FSMContext):
    """Обработка одного города для мультиразмещения"""
    city_name = message.text.strip()

    if not city_name:
        await message.answer("Введите название города:")
        return

    # Ищем город
    result = await validate_city_nominatim(city_name)

    if result['valid']:
        city_data = result['data']

        # Сохраняем полные данные города
        selected_cities = [{
            'name': city_data['name'],
            'full_address': city_data['full_address'],
            'lat': city_data.get('lat'),
            'lon': city_data.get('lon'),
            'type': city_data.get('type')
        }]

        # Сохраняем город и запрашиваем количество
        await state.update_data(
            selected_cities=selected_cities,
            cities=[city_data['name']]  # Сохраняем как список из одного города
        )
        await state.set_state(ProductStates.waiting_for_quantity)

        await message.answer(
            f"✅ Город подтвержден!\n"
            f"🏙️ {city_data['name']}\n"
            f"📍 {city_data['full_address']}\n\n"
            "Теперь введите количество объявлений для этого города:",
            reply_markup=ReplyKeyboardRemove()
        )

    else:
        await message.answer(
            f"❌ Город '{city_name}' не найден.\n"
            "Попробуйте ввести другое название:"
        )

async def ask_single_city_for_multiple(message: Message, user_name: str = ""):
    """Запрос одного города для мультиразмещения"""
    greeting = f"{user_name}, " if user_name else ""

    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="✅ Завершить ввод городов")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

    await message.answer(
        f"{greeting}введите название города для мультиразмещения:\n\n"
        "🏙️ Будет создано несколько объявлений в одном городе\n"
        "🔍 Город будет проверен\n"
        "✅ Нажмите кнопку чтобы завершить ввод",
        reply_markup=keyboard
    )


@router.message(StateFilter(ProductStates.waiting_for_city_input))
async def process_city_input(message: Message, state: FSMContext):
    """Обработка ввода города с проверкой на команду завершения"""
    # Проверяем, не является ли это командой завершения
    if message.text == "✅ Завершить ввод городов":
        await finish_city_input(message, state)
        return

    city_name = message.text.strip()

    if not city_name:
        await message.answer("Введите название города:")
        return

    # Ищем город через Nominatim
    result = await validate_city_nominatim(city_name)

    if result['valid']:
        city_data = result['data']

        # Сохраняем временные данные для подтверждения
        await state.update_data(temp_city=city_data)

        builder = InlineKeyboardBuilder()
        builder.button(text="✅ Да, верно", callback_data="city_confirm")
        builder.button(text="❌ Нет, другой город", callback_data="city_reject")
        builder.adjust(2)

        await message.answer(
            f"🔍 Найден город:\n"
            f"🏙️ {city_data['name']}\n"
            f"📍 {city_data['full_address']}\n\n"
            "Это правильный город?",
            reply_markup=builder.as_markup()
        )

        await state.set_state(ProductStates.waiting_for_city_confirmation)

    else:
        await message.answer(
            f"❌ Город '{city_name}' не найден.\n"
            "Попробуйте ввести другое название:"
        )


@router.message(StateFilter(ProductStates.waiting_for_quantity))
async def handle_quantity_input(message: Message, state: FSMContext):
    """Общий обработчик количества - определяет контекст"""
    data = await state.get_data()
    placement_method = data.get('placement_method')

    if placement_method == "multiple_in_city":
        await process_quantity_for_multiple(message, state)
    elif placement_method == "by_quantity":
        await process_quantity_from_xml(message, state)
    elif placement_method == "metro":
        await process_metro_quantity(message, state)
    else:
        # По умолчанию - обычная обработка
        await process_general_quantity(message, state)


@router.message(StateFilter(ProductStates.waiting_for_quantity))
async def process_quantity_from_xml(message: Message, state: FSMContext):
    """Обработка количества для метода из XML"""
    try:
        quantity = int(message.text.strip())
        cities = load_cities_from_xml()

        if quantity <= 0:
            await message.answer("Количество должно быть положительным числом. Введите количество:")
            return

        if quantity > len(cities):
            await message.answer(f"Максимальное количество: {len(cities)}. Введите меньшее число:")
            return

        # Берем первые N городов по населению
        selected_cities = [city['name'] for city in cities[:quantity]]

        await state.update_data(
            cities=selected_cities,
            quantity=quantity
        )

        user_name = message.from_user.first_name
        cities_list = ", ".join(selected_cities)

        await message.answer(
            f"{user_name}, ✅ выбрано {quantity} городов:\n{cities_list}"
        )

        await state.set_state(ProductStates.waiting_for_start_date)
        await ask_start_date(message, user_name)

    except ValueError:
        await message.answer("Количество должно быть числом. Введите количество:")

async def process_quantity_for_multiple(message: Message, state: FSMContext):
    """Обработка количества для мультиразмещения в одном городе"""
    try:
        quantity = int(message.text.strip())

        if quantity <= 0:
            await message.answer("Количество должно быть положительным числом. Введите количество:")
            return

        if quantity > 100:
            await message.answer("Максимальное количество: 100. Введите меньшее число:")
            return

        data = await state.get_data()
        selected_cities = data.get('selected_cities', [])

        if not selected_cities:
            await message.answer(
                "❌ Ошибка: город не выбран.\n"
                "Пожалуйста, начните заново с выбора города."
            )
            return

        # Берем первый (и единственный) город из списка
        city_data = selected_cities[0]

        await state.update_data(
            quantity=quantity,
            cities=[city_data['name']],  # Сохраняем название города
            selected_cities=selected_cities  # Сохраняем полные данные
        )

        user_name = message.from_user.first_name

        await message.answer(
            f"{user_name}, ✅ настроено мультиразмещение:\n"
            f"🏙️ Город: {city_data['name']}\n"
            f"📊 Количество объявлений: {quantity}\n"
            f"📍 Будет сгенерировано {quantity} разных адресов"
        )

        await state.set_state(ProductStates.waiting_for_start_date)
        await ask_start_date(message, user_name)

    except ValueError:
        await message.answer("Количество должно быть числом. Введите количество:")


async def process_general_quantity(message: Message, state: FSMContext):
    """Обработка количества для общего случая"""
    try:
        quantity = int(message.text.strip())

        if quantity <= 0:
            await message.answer("Количество должно быть положительным числом. Введите количество:")
            return

        await state.update_data(quantity=quantity)

        user_name = message.from_user.first_name
        await message.answer(f"{user_name}, количество установлено: {quantity}")

        await state.set_state(ProductStates.waiting_for_start_date)
        await ask_start_date(message, user_name)

    except ValueError:
        await message.answer("Количество должно быть числом. Введите количество:")

async def finish_city_input(message: Message, state: FSMContext):
    """Завершение ввода городов"""
    data = await state.get_data()
    selected_cities = data.get('selected_cities', [])

    if not selected_cities:
        # Если городов нет, предлагаем начать заново или пропустить
        builder = InlineKeyboardBuilder()
        builder.button(text="🔄 Начать ввод городов", callback_data="cities_restart")
        builder.button(text="⏩ Пропустить без городов", callback_data="cities_skip")
        builder.adjust(1)

        await message.answer(
            "❌ Вы не добавили ни одного города.\n\n"
            "Выберите действие:",
            reply_markup=builder.as_markup()
        )
        return

    # Сохраняем только названия городов для дальнейшей обработки
    city_names = [city['name'] for city in selected_cities]
    await state.update_data(cities=city_names)
    await state.set_state(ProductStates.waiting_for_start_date)

    user_name = message.from_user.first_name
    cities_list = ", ".join(city_names)

    await message.answer(
        f"{user_name}, ✅ завершен ввод городов!\n"
        f"🏙️ Добавлено городов: {len(selected_cities)}\n"
        f"📍 Список: {cities_list}",
        reply_markup=ReplyKeyboardRemove()
    )

    await ask_start_date(message, user_name)


@router.message(StateFilter(ProductStates.waiting_for_city_input))
async def process_single_city_input(message: Message, state: FSMContext):
    """Обработка ввода одного города"""
    city_name = message.text.strip()

    if not city_name:
        await message.answer("Введите название города:")
        return

    # Ищем город через Nominatim
    result = await validate_city_nominatim(city_name)

    if result['valid']:
        city_data = result['data']

        # Сохраняем временные данные для подтверждения
        await state.update_data(temp_city=city_data)

        builder = InlineKeyboardBuilder()
        builder.button(text="✅ Да, верно", callback_data="city_confirm")
        builder.button(text="❌ Нет, другой город", callback_data="city_reject")
        builder.adjust(2)

        await message.answer(
            f"🔍 Найден город:\n"
            f"🏙️ {city_data['name']}\n"
            f"📍 {city_data['full_address']}\n\n"
            "Это правильный город?",
            reply_markup=builder.as_markup()
        )

        await state.set_state(ProductStates.waiting_for_city_confirmation)

    else:
        await message.answer(
            f"❌ Город '{city_name}' не найден.\n"
            "Попробуйте ввести другое название:"
        )


@router.callback_query(F.data == "cities_restart", StateFilter(ProductStates.waiting_for_city_input))
async def restart_city_input(callback: CallbackQuery, state: FSMContext):
    """Перезапуск ввода городов"""
    await state.update_data(selected_cities=[])
    await callback.message.edit_text("Введите название первого города:")
    await callback.answer()


@router.callback_query(F.data == "cities_skip", StateFilter(ProductStates.waiting_for_city_input))
async def skip_city_input(callback: CallbackQuery, state: FSMContext):
    """Пропуск ввода городов"""
    await state.update_data(cities=[])
    await state.set_state(ProductStates.waiting_for_start_date)

    user_name = callback.from_user.first_name
    await callback.message.edit_text(f"{user_name}, размещение будет без привязки к городам.")

    await ask_start_date(callback.message, user_name)


@router.callback_query(StateFilter(ProductStates.waiting_for_city_confirmation), F.data == "city_confirm")
async def confirm_city(callback: CallbackQuery, state: FSMContext):
    """Подтверждение города - сохраняем полные данные"""
    data = await state.get_data()
    city_data = data.get('temp_city')
    selected_cities = data.get('selected_cities', [])

    # Добавляем полные данные города в список
    selected_cities.append({
        'name': city_data['name'],
        'full_address': city_data['full_address'],
        'lat': city_data.get('lat'),
        'lon': city_data.get('lon'),
        'type': city_data.get('type')
    })

    await state.update_data(selected_cities=selected_cities)

    # Возвращаемся к вводу следующего города
    await state.set_state(ProductStates.waiting_for_city_input)

    # Показываем клавиатуру для завершения
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="✅ Завершить ввод городов")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

    await callback.message.edit_text(
        f"✅ Город добавлен!\n"
        f"🏙️ {city_data['name']}\n"
        f"📍 {city_data['full_address']}\n\n"
        f"📊 Всего городов: {len(selected_cities)}\n\n"
        "Введите следующий город или завершите ввод:"
    )

    # Отправляем новое сообщение с клавиатурой
    await callback.message.answer(
        "Можете продолжить ввод городов:",
        reply_markup=keyboard
    )


@router.callback_query(StateFilter(ProductStates.waiting_for_city_confirmation), F.data == "city_reject")
async def reject_city(callback: CallbackQuery, state: FSMContext):
    """Отклонение города"""
    await state.set_state(ProductStates.waiting_for_city_input)
    await callback.message.edit_text("Введите другой город:")

@router.message(StateFilter(ProductStates.waiting_for_main_images), F.media_group_id)
async def handle_main_images_album(message: Message, album: list[Message], state: FSMContext):
    """Обработка альбома основных изображений"""
    if not album:
        return

    photo_files = []

    for msg in album:
        if msg.photo:
            # Берем самое большое фото
            largest_photo = msg.photo[-1]
            photo_files.append(largest_photo.file_id)

    if photo_files:
        # Сохраняем все фото из альбома
        data = await state.get_data()
        main_images = data.get('main_images', [])
        main_images.extend(photo_files)

        await state.update_data(main_images=main_images)

        user_name = message.from_user.first_name
        await message.answer(
            f"{user_name}, ✅ добавлен альбом с {len(photo_files)} основными фото! Всего основных фото: {len(main_images)}\n\n"
            "Продолжайте отправлять фото или нажмите /finish_main_images чтобы завершить."
        )


@router.message(StateFilter(ProductStates.waiting_for_additional_images), F.media_group_id)
async def handle_additional_images_album(message: Message, album: list[Message], state: FSMContext):
    """Обработка альбома дополнительных изображений"""
    if not album:
        return

    photo_files = []

    for msg in album:
        if msg.photo:
            # Берем самое большое фото
            largest_photo = msg.photo[-1]
            photo_files.append(largest_photo.file_id)

    if photo_files:
        # Сохраняем все фото из альбома
        data = await state.get_data()
        additional_images = data.get('additional_images', [])
        additional_images.extend(photo_files)

        await state.update_data(additional_images=additional_images)

        user_name = message.from_user.first_name
        total_count = len(additional_images)

        await message.answer(
            f"{user_name}, ✅ добавлен альбом с {len(photo_files)} дополнительными фото! Всего дополнительных фото: {total_count}\n\n"
            "Продолжайте отправлять фото или нажмите /finish_additional_images чтобы завершить."
        )

@router.message(Command("new_product"))
async def new_product_command(message: Message, state: FSMContext):
    await state.clear()
    await db.clear_user_state(message.from_user.id)

    # Генерируем GUID для нового товара
    product_guid = generate_guid()
    await state.update_data(
        product_id=product_guid,
        main_images=[],
        additional_images=[],
        shuffle_images=False,
        avito_delivery=False,
        delivery_services=[]
    )

    await state.set_state(ProductStates.waiting_for_category)

    user_name = message.from_user.first_name
    await show_main_categories(message, user_name)


@router.callback_query(F.data == "back_categories")
async def back_to_categories(callback: CallbackQuery, state: FSMContext):
    """Вернуться к выбору категорий"""
    await state.set_state(ProductStates.waiting_for_category)
    user_name = callback.from_user.first_name
    await show_main_categories(callback.message, user_name)


@router.callback_query(F.data.startswith("cat_"))
async def process_main_category(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора основной категории"""
    API_KEY = "11596b4e-f890-4a88-b439-e9da09bb9c03"
    #validation_result = await validate_city_nominatim("мазсква")
    #print(validation_result)
    #validation_result2 = await validate_city_nominatim("Воронеж")
    #print(validation_result2)
    #validation_result3 = await validate_city_nominatim("Ямное Воронежская область")
    #print(validation_result3)
    category_id = callback.data[4:]  # Убираем "cat_"
    category_data = config.AVITO_CATEGORIES.get(category_id)

    if not category_data:
        await callback.answer("Категория не найдена")
        return

    await state.update_data(main_category_id=category_id, main_category_name=category_data["name"])
    await state.set_state(ProductStates.waiting_for_subcategory)

    user_name = callback.from_user.first_name
    await callback.message.edit_text(f"{user_name}, основная категория: {category_data['name']}")
    await show_subcategories(callback.message, category_id, user_name)


@router.callback_query(F.data.startswith("sub_"))
async def process_subcategory(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора подкатегории"""
    subcategory_id = callback.data[4:]  # Убираем "sub_"

    # Получаем данные о выбранной категории
    data = await state.get_data()
    main_category_id = data.get('main_category_id')
    main_category_name = data.get('main_category_name')

    if not main_category_id:
        await callback.answer("Ошибка: основная категория не выбрана")
        return

    # Находим название подкатегории
    category_data = config.AVITO_CATEGORIES.get(main_category_id)
    subcategories = category_data.get("subcategories", {})
    subcategory_name = subcategories.get(subcategory_id)

    if not subcategory_name:
        await callback.answer("Подкатегория не найдена")
        return

    # Получаем ID категории для Avito
    avito_category_id = config.CATEGORY_IDS.get(subcategory_id, config.CATEGORY_IDS.get(main_category_id))

    await state.update_data(
        category=avito_category_id,
        category_name=f"{main_category_name} - {subcategory_name}",
        subcategory_name=subcategory_name
    )
    await state.set_state(ProductStates.waiting_for_title)

    user_name = callback.from_user.first_name
    await callback.message.edit_text(
        f"{user_name}, ✅ категория выбрана: {main_category_name} - {subcategory_name}\n\n"
        "Теперь введите заголовок объявления:"
    )


@router.message(StateFilter(ProductStates.waiting_for_title))
async def process_product_title(message: Message, state: FSMContext):
    """Обработка заголовка товара"""
    title = message.text.strip()
    if not title:
        await message.answer("Заголовок не может быть пустым. Введите заголовок объявления:")
        return

    if len(title) > 100:
        await message.answer("Заголовок не должен превышать 100 символов. Введите более короткий заголовок:")
        return

    await state.update_data(title=title)
    await state.set_state(ProductStates.waiting_for_description)

    user_name = message.from_user.first_name
    await message.answer(
        f"{user_name}, введите текст объявления, не менее 100 и не более 3500 символов:"
    )


@router.message(StateFilter(ProductStates.waiting_for_description))
async def process_product_description(message: Message, state: FSMContext):
    """Обработка описания товара"""
    description = message.text.strip()

    if len(description) < 100:
        await message.answer(
            "Описание должно содержать не менее 100 символов. Пожалуйста, напишите более подробное описание:")
        return

    if len(description) > 3500:
        await message.answer("Описание не должно превышать 3500 символов. Сократите текст и попробуйте снова:")
        return

    await state.update_data(description=description)
    await state.set_state(ProductStates.waiting_for_price_type)

    user_name = message.from_user.first_name
    await show_price_type_options(message, user_name)


@router.callback_query(F.data == "price_fixed")
async def process_price_fixed(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора фиксированной цены"""
    await state.update_data(price_type="fixed")
    await state.set_state(ProductStates.waiting_for_price)

    user_name = callback.from_user.first_name
    await callback.message.edit_text(
        f"{user_name}, введите фиксированную цену в рублях (например: 2500):"
    )


@router.callback_query(F.data == "price_range")
async def process_price_range(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора диапазона цен"""
    await state.update_data(price_type="range")
    await state.set_state(ProductStates.waiting_for_price_range)

    user_name = callback.from_user.first_name
    await callback.message.edit_text(
        f"{user_name}, введите диапазон цен в формате МИНИМУМ-МАКСИМУМ (например: 1200-1500):"
    )


@router.callback_query(F.data == "price_skip")
async def process_price_skip(callback: CallbackQuery, state: FSMContext):
    """Обработка пропуска цены"""
    await state.update_data(price_type="none", price=None, price_min=None, price_max=None)
    await state.set_state(ProductStates.waiting_for_phone)

    user_name = callback.from_user.first_name
    await callback.message.edit_text(
        f"{user_name}, цена не будет указана в объявлении."
    )

    # Переходим к новому запросу телефона с кнопкой
    await ask_phone_number(callback.message, user_name)

@router.message(StateFilter(ProductStates.waiting_for_price))
async def process_fixed_price(message: Message, state: FSMContext):
    """Обработка фиксированной цены"""
    """Обработка фиксированной цены"""
    try:
        price = int(message.text.strip())
        if price <= 0:
            await message.answer("Цена должна быть положительным числом. Введите цену еще раз:")
            return

        await state.update_data(price=price, price_min=None, price_max=None)
        await state.set_state(ProductStates.waiting_for_phone)

        user_name = message.from_user.first_name
        await message.answer(f"✅ Цена установлена: {price} руб.")

        # Переходим к новому запросу телефона с кнопкой
        await ask_phone_number(message, user_name)

    except ValueError:
        await message.answer("Цена должна быть числом. Введите цену еще раз:")


@router.message(StateFilter(ProductStates.waiting_for_price_range))
async def process_price_range_input(message: Message, state: FSMContext):
    """Обработка диапазона цен"""
    text = message.text.strip()

    # Проверяем формат диапазона
    if '-' not in text:
        await message.answer("Неверный формат. Введите диапазон в формате МИНИМУМ-МАКСИМУМ (например: 1200-1500):")
        return

    try:
        min_price, max_price = text.split('-')
        min_price = int(min_price.strip())
        max_price = int(max_price.strip())

        if min_price <= 0 or max_price <= 0:
            await message.answer("Цены должны быть положительными числами. Введите диапазон еще раз:")
            return

        if min_price >= max_price:
            await message.answer("Минимальная цена должна быть меньше максимальной. Введите диапазон еще раз:")
            return

        await state.update_data(price_min=min_price, price_max=max_price, price=None)
        await state.set_state(ProductStates.waiting_for_phone)

        user_name = message.from_user.first_name
        await message.answer(f"✅ Диапазон цен установлен: {min_price}-{max_price} руб.")

        # Переходим к новому запросу телефона с кнопкой
        await ask_phone_number(message, user_name)

    except ValueError:
        await message.answer(
            "Цены должны быть числами. Введите диапазон в формате МИНИМУМ-МАКСИМУМ (например: 1200-1500):")

def normalize_phone(phone: str) -> str:
    """Нормализация телефонного номера к формату +7XXXXXXXXXX"""
    # Удаляем все нецифровые символы, кроме +
    cleaned = re.sub(r'[^\d+]', '', phone)

    # Обрабатываем разные форматы
    if cleaned.startswith('8') and len(cleaned) == 11:
        cleaned = '+7' + cleaned[1:]
    elif cleaned.startswith('7') and len(cleaned) == 11:
        cleaned = '+' + cleaned
    elif len(cleaned) == 10:
        cleaned = '+7' + cleaned
    elif cleaned.startswith('+7') and len(cleaned) == 12:
        pass  # Уже в правильном формате
    elif cleaned.startswith('+') and len(cleaned) == 12:
        pass  # Международный формат

    return cleaned

def is_valid_phone(phone: str) -> bool:
    """Проверка валидности телефонного номера"""
    normalized = normalize_phone(phone)

    # Основная проверка - российские номера
    if re.match(r'^(\+7|7|8)\d{10}$', normalized.replace('+', '').replace(' ', '')):
        return True

    # Проверяем визуальные форматы
    patterns = [
        r'^\+7\s?\(\d{3}\)\s?\d{3}-\d{2}-\d{2}$',
        r'^8\s?\(\d{3}\)\s?\d{3}-\d{2}-\d{2}$',
        r'^8\s?\d{3}\s?\d{3}\s?\d{2}\s?\d{2}$',
        r'^\+7\s?\d{3}\s?\d{3}\s?\d{2}\s?\d{2}$',
        r'^\d{11}$',
        r'^\d{10}$'
    ]

    cleaned_phone = re.sub(r'[^\d]', '', phone)
    if len(cleaned_phone) in [10, 11]:
        return True

    for pattern in patterns:
        if re.match(pattern, phone.strip()):
            return True

    return False

@router.message(StateFilter(ProductStates.waiting_for_phone), F.contact)
async def process_contact_phone(message: Message, state: FSMContext):
    """Обработка номера телефона из контакта"""
    contact = message.contact
    phone_number = contact.phone_number

    # Нормализуем номер
    normalized_phone = normalize_phone(phone_number)

    if not is_valid_phone(normalized_phone):
        await message.answer(
            "❌ Неверный формат номера телефона из контакта.\n"
            "Пожалуйста, введите номер вручную:",
            reply_markup=ReplyKeyboardRemove()
        )
        return

    await state.update_data(contact_phone=normalized_phone, display_phone=phone_number)
    await state.set_state(ProductStates.waiting_for_contact_method)

    # Убираем клавиатуру
    await message.answer(
        f"✅ Номер получен: {phone_number}",
        reply_markup=ReplyKeyboardRemove()
    )

    user_name = message.from_user.first_name
    await show_contact_methods(message, user_name)


@router.message(StateFilter(ProductStates.waiting_for_phone), F.text == "✏️ Ввести вручную")
async def process_manual_phone_input(message: Message, state: FSMContext):
    """Обработка выбора ручного ввода номера"""
    await message.answer(
        "Введите номер телефона вручную в одном из форматов:\n\n"
        "Корректные примеры:\n"
        "— +7 (495) 777-10-66\n"
        "— (81374) 4-55-75\n"
        "— 8 905 207 04 90\n"
        "— +7 905 2070490\n"
        "— 88123855085",
        reply_markup=ReplyKeyboardRemove()
    )

@router.message(StateFilter(ProductStates.waiting_for_phone))
async def process_phone_message(message: Message, state: FSMContext):
    """Обработка ручного ввода номера телефона"""
    phone = message.text.strip()

    # Если это команда ручного ввода, уже обработана выше
    if phone == "✏️ Ввести вручную":
        return

    if not is_valid_phone(phone):
        await message.answer(
            "❌ Неверный формат телефона. Пожалуйста, введите номер в одном из допустимых форматов:\n\n"
            "Корректные примеры:\n"
            "— +7 (495) 777-10-66\n"
            "— (81374) 4-55-75\n"
            "— 8 905 207 04 90\n"
            "— +7 905 2070490\n"
            "— 88123855085"
        )
        return

    # Нормализуем номер для хранения
    normalized_phone = normalize_phone(phone)
    await state.update_data(contact_phone=normalized_phone, display_phone=phone)
    await state.set_state(ProductStates.waiting_for_contact_method)

    user_name = message.from_user.first_name
    await message.answer(f"✅ Номер подтвержден: {phone}")
    await show_contact_methods(message, user_name)

@router.callback_query(F.data.startswith("contact_"))
async def process_contact_method(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора способа связи"""
    contact_method = callback.data[8:]  # Убираем "contact_"

    contact_methods = {
        "both": "По телефону и в сообщении",
        "phone": "По телефону",
        "message": "В сообщениях"
    }

    method_name = contact_methods.get(contact_method, "Не указано")
    await state.update_data(contact_method=contact_method)
    await state.set_state(ProductStates.waiting_for_main_images)

    user_name = callback.from_user.first_name
    await callback.message.edit_text(
        f"{user_name}, способ связи: {method_name}\n\n"
        "Теперь отправьте в этот чат ОСНОВНЫЕ фото объявления (одно или несколько изображений одним сообщением).\n\n"
        "📸 Вы можете отправить до 10 фотографий.\n"
        "После отправки всех основных фото нажмите /finish_main_images"
    )


# Обработка основных изображений
@router.message(StateFilter(ProductStates.waiting_for_main_images), F.media_group_id)
async def process_main_album_images(message: Message, state: FSMContext):
    """Обработка альбома основных изображений"""
    media_group_id = message.media_group_id

    if media_group_id not in temp_main_albums:
        temp_main_albums[media_group_id] = {
            'user_id': message.from_user.id,
            'photos': [],
            'created_at': datetime.now()
        }

    # Добавляем фото в альбом
    if message.photo:
        # Берем самое большое фото
        largest_photo = message.photo[-1]
        temp_main_albums[media_group_id]['photos'].append(largest_photo.file_id)

    # Ограничиваем количество фото до 10
    if len(temp_main_albums[media_group_id]['photos']) > 10:
        temp_main_albums[media_group_id]['photos'] = temp_main_albums[media_group_id]['photos'][:10]


@router.message(StateFilter(ProductStates.waiting_for_main_images), F.photo)
async def process_main_single_image(message: Message, state: FSMContext):
    """Обработка одиночного основного изображения"""
    if message.media_group_id:
        # Это часть альбома, пропускаем - обработается в handle_main_images_album
        return

    # Одиночное фото
    largest_photo = message.photo[-1]
    photo_file_id = largest_photo.file_id

    data = await state.get_data()
    main_images = data.get('main_images', [])
    main_images.append(photo_file_id)

    await state.update_data(main_images=main_images)

    user_name = message.from_user.first_name
    await message.answer(
        f"{user_name}, ✅ получено 1 основное изображение! Всего основных фото: {len(main_images)}\n\n"
        "Продолжайте отправлять фото или нажмите /finish_main_images чтобы завершить."
    )


@router.message(StateFilter(ProductStates.waiting_for_additional_images), F.photo)
async def process_additional_single_image(message: Message, state: FSMContext):
    """Обработка одиночного дополнительного изображения"""
    if message.media_group_id:
        # Это часть альбома, пропускаем - обработается в handle_additional_images_album
        return

    # Одиночное фото - добавляем к существующим
    data = await state.get_data()
    additional_images = data.get('additional_images', [])

    largest_photo = message.photo[-1]
    additional_images.append(largest_photo.file_id)

    await state.update_data(additional_images=additional_images)

    user_name = message.from_user.first_name
    await message.answer(
        f"{user_name}, ✅ дополнительное изображение добавлено! Всего дополнительных фото: {len(additional_images)}\n\n"
        "Продолжайте отправлять фото или нажмите /finish_additional_images чтобы завершить."
    )

@router.message(Command("finish_main_images"))
async def finish_main_images_command(message: Message, state: FSMContext):
    """Завершение добавления основных изображений"""
    data = await state.get_data()
    main_images = data.get('main_images', [])

    await state.set_state(ProductStates.waiting_for_additional_images)

    user_name = message.from_user.first_name
    if main_images:
        await message.answer(
            f"{user_name}, ✅ завершено добавление основных изображений! Всего: {len(main_images)}\n\n"
            "Теперь переходим к дополнительным фотографиям."
        )
    else:
        await message.answer(
            f"{user_name}, основных изображений нет. Переходим к дополнительным фотографиям."
        )

    await ask_additional_images(message, state, user_name)


@router.message(Command("cities_status"), StateFilter(ProductStates.waiting_for_city_input))
async def show_cities_status(message: Message, state: FSMContext):
    """Показать текущий статус ввода городов"""
    data = await state.get_data()
    selected_cities = data.get('selected_cities', [])

    if not selected_cities:
        await message.answer("📭 Пока не добавлено ни одного города.")
        return

    cities_text = "📋 Добавленные города:\n\n"
    for i, city in enumerate(selected_cities, 1):
        cities_text += f"{i}. {city['name']}\n"
        cities_text += f"   📍 {city['full_address']}\n\n"

    cities_text += f"📊 Всего: {len(selected_cities)} городов"

    await message.answer(cities_text)

@router.message(Command("finish_additional_images"))
async def finish_additional_images_command(message: Message, state: FSMContext):
    """Завершение добавления дополнительных изображений"""
    data = await state.get_data()
    additional_images = data.get('additional_images', [])

    await state.set_state(ProductStates.waiting_for_shuffle_images)

    user_name = message.from_user.first_name

    # Показываем итоговую статистику
    main_images = data.get('main_images', [])
    total_main = len(main_images)
    total_additional = len(additional_images)
    total_all = total_main + total_additional

    await message.answer(
        f"{user_name}, завершено добавление дополнительных фото!\n\n"
        f"📊 Статистика фото:\n"
        f"• Основные: {total_main}\n"
        f"• Дополнительные: {total_additional}\n"
        f"• Всего: {total_all}\n\n"
        "Теперь нужно решить, перемешивать ли фото."
    )

    await ask_shuffle_images(message, state, user_name)

@router.callback_query(F.data.startswith("shuffle_"))
async def process_shuffle_choice(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора перемешивания фото"""
    shuffle_choice = callback.data[8:]  # Убираем "shuffle_"

    shuffle_images = (shuffle_choice == "yes")
    await state.update_data(shuffle_images=shuffle_images)
    await state.set_state(ProductStates.waiting_for_avito_delivery)

    user_name = callback.from_user.first_name
    choice_text = "перемешаны" if shuffle_images else "оставлены в исходном порядке"

    await callback.message.edit_text(
        f"{user_name}, фото будут {choice_text}.\n\n"
        "Теперь уточним настройки доставки."
    )

    await ask_avito_delivery(callback.message, user_name)

@router.callback_query(F.data.startswith("delivery_"))
async def process_delivery_choice(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора Авито доставки"""
    delivery_choice = callback.data[9:]  # Убираем "delivery_"

    avito_delivery = (delivery_choice == "yes")
    await state.update_data(avito_delivery=avito_delivery)

    user_name = callback.from_user.first_name

    if avito_delivery:
        await state.set_state(ProductStates.waiting_for_delivery_services)
        await ask_delivery_services(callback.message, state, user_name)
    else:
        # Если доставка не нужна, переходим к вопросу о мультиобъявлении
        await state.set_state(ProductStates.waiting_for_multioffer)
        await ask_multioffer(callback.message, user_name)


@router.callback_query(F.data.startswith("service_"))
async def process_delivery_service(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора службы доставки"""
    service_code = callback.data[8:]  # Убираем "service_"

    if service_code == "done":
        # Переходим к вопросу о скидке на доставку
        await state.set_state(ProductStates.waiting_for_delivery_discount)
        user_name = callback.from_user.first_name
        await ask_delivery_discount(callback.message, user_name)
        return

    data = await state.get_data()
    selected_services = data.get('delivery_services', [])

    # Если выбрана "Выключена", очищаем другие выборы
    if service_code == "disabled":
        selected_services = ["disabled"]
    elif "disabled" in selected_services:
        selected_services.remove("disabled")

    # Переключаем выбор службы
    if service_code in selected_services:
        selected_services.remove(service_code)
    else:
        selected_services.append(service_code)

    await state.update_data(delivery_services=selected_services)

    # Обновляем клавиатуру с текущим состоянием выборов
    await update_delivery_services_keyboard(callback.message, state, callback.from_user.first_name)


# Добавьте эти функции после существующих вспомогательных функций

async def ask_delivery_discount(message: Message, user_name: str = ""):
    """Запрос о скидке на доставку"""
    builder = InlineKeyboardBuilder()

    builder.button(text="🆓 Бесплатная доставка", callback_data="discount_free")
    builder.button(text="💰 Скидка на доставку", callback_data="discount_discount")
    builder.button(text="🚫 Нет скидки", callback_data="discount_none")

    builder.adjust(1)

    greeting = f"{user_name}, " if user_name else ""
    await message.answer(
        f"{greeting}есть ли скидка на доставку?\n\n"
        "Для товаров с ценой выше 500 рублей можно настроить:\n"
        "• 🆓 Бесплатная доставка - доставка бесплатная для покупателя\n"
        "• 💰 Скидка на доставку - у покупателя появятся скидка на доставку\n"
        "• 🚫 Нет скидки - скидки на доставку нет",
        reply_markup=builder.as_markup()
    )


async def ask_multioffer(message: Message, user_name: str = ""):
    """Запрос о мультиобъявлении"""
    builder = InlineKeyboardBuilder()

    builder.button(text="✅ Да", callback_data="multioffer_yes")
    builder.button(text="❌ Нет", callback_data="multioffer_no")

    builder.adjust(2)

    greeting = f"{user_name}, " if user_name else ""
    await message.answer(
        f"{greeting}является ли объявление мультиобъявлением?",
        reply_markup=builder.as_markup()
    )

@router.callback_query(F.data.startswith("discount_"))
async def process_delivery_discount(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора скидки на доставку"""
    discount_type = callback.data[9:]  # Убираем "discount_"

    discount_names = {
        "free": "бесплатная доставка",
        "discount": "скидка на доставку",
        "none": "нет скидки"
    }

    await state.update_data(delivery_discount=discount_type)
    await state.set_state(ProductStates.waiting_for_multioffer)

    user_name = callback.from_user.first_name
    discount_text = discount_names.get(discount_type, "не указано")

    await callback.message.edit_text(
        f"{user_name}, скидка на доставку: {discount_text}\n\n"
        "Теперь уточним тип объявления."
    )

    await ask_multioffer(callback.message, user_name)

@router.callback_query(F.data.startswith("multioffer_"))
async def process_multioffer(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора мультиобъявления"""
    multioffer_choice = callback.data[11:]  # Убираем "multioffer_"

    multioffer = (multioffer_choice == "yes")
    await state.update_data(multioffer=multioffer)

    user_name = callback.from_user.first_name
    multioffer_text = "мультиобъявлением" if multioffer else "обычным объявлением"

    await callback.message.edit_text(
        f"{user_name}, объявление является {multioffer_text}.\n\n"
        "Теперь укажем дополнительные параметры."
    )

    # Переходим к вводу бренда вручную
    await state.set_state(ProductStates.waiting_for_brand)
    await ask_brand_manual(callback.message, user_name)


# Обработчики для брендов
@router.callback_query(F.data.startswith("brand_"))
async def process_brand(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора бренда"""
    brand_data = callback.data[6:]  # Убираем "brand_"

    if brand_data == "show_all":
        # Показать все бренды
        brands = load_brands()
        builder = InlineKeyboardBuilder()

        for brand in brands:
            builder.button(text=brand, callback_data=f"brand_{brand}")

        builder.button(text="✏️ Ввести вручную", callback_data="brand_custom")
        builder.adjust(1)

        await callback.message.edit_text(
            "Выберите бренд из списка:",
            reply_markup=builder.as_markup()
        )
        return

    if brand_data == "custom":
        await callback.message.edit_text("Введите название бренда:")
        await state.set_state(ProductStates.waiting_for_brand)
        return

    await state.update_data(brand=brand_data)

    # Проверяем, нужен ли размер для этой категории
    data = await state.get_data()
    category_name = data.get('category_name', '')

    needs_size = any(size_cat in category_name for size_cat in SIZE_CATEGORIES)

    user_name = callback.from_user.first_name
    await callback.message.edit_text(f"{user_name}, бренд: {brand_data}")

    if needs_size:
        await state.set_state(ProductStates.waiting_for_size)
        await ask_size(callback.message, user_name)
    else:
        await state.set_state(ProductStates.waiting_for_condition)
        await ask_condition(callback.message, user_name)


@router.message(StateFilter(ProductStates.waiting_for_brand))
async def process_brand_input(message: Message, state: FSMContext):
    """Обработка ручного ввода бренда с поиском"""
    brand_input = message.text.strip()

    # Проверяем, не является ли это текстом кнопки
    if brand_input in ["✏️ Ввести другой бренд", "Ввести другой бренд"]:
        await message.answer("Введите название бренда:")
        return

    if not brand_input:
        await message.answer("Бренд не может быть пустым. Введите название бренда:")
        return

    # Сначала проверяем точное совпадение
    if is_valid_brand(brand_input):
        await state.update_data(brand=brand_input)
        await process_brand_success(message, state, message.from_user.first_name)
        return

    # Если точного совпадения нет, ищем похожие
    similar_brands = search_brands(brand_input)

    if similar_brands:
        # Показываем похожие бренды
        builder = InlineKeyboardBuilder()

        for similar_brand in similar_brands:
            builder.button(text=similar_brand, callback_data=f"exact_brand_{similar_brand}")

        builder.button(text="✏️ Ввести другой бренд", callback_data="br_retry")
        builder.adjust(1)

        similar_list = "\n".join([f"• {brand}" for brand in similar_brands])

        await message.answer(
            f"❌ Бренд '{brand_input}' не найден, но есть похожие:\n\n"
            f"{similar_list}\n\n"
            "Выберите подходящий вариант или введите бренд заново:",
            reply_markup=builder.as_markup()
        )
    else:
        await message.answer(
            f"❌ Бренд '{brand_input}' не найден в базе.\n\n"
            "Пожалуйста, проверьте написание и введите бренд еще раз:"
        )

@router.callback_query(F.data == "br_retry", StateFilter(ProductStates.waiting_for_brand))
async def process_brand_retry(callback: CallbackQuery, state: FSMContext):
    """Повторный ввод бренда - обрабатываем нажатие кнопки"""
    await callback.message.edit_text("Введите название бренда:")
    # Состояние остается ProductStates.waiting_for_brand
    await callback.answer()


async def ask_bag_type(message: Message, user_name: str = ""):
    """Запрос вида сумки"""
    bag_params = get_bag_parameters()
    bag_type_params = bag_params.get('bag_type', {})

    builder = InlineKeyboardBuilder()

    for value_name, value_code in bag_type_params.get('values', []):
        builder.button(text=value_name, callback_data=f"bag_type_{value_code}")

    builder.adjust(1)

    greeting = f"{user_name}, " if user_name else ""
    await message.answer(
        f"{greeting}выберите вид сумки:",
        reply_markup=builder.as_markup()
    )


@router.callback_query(F.data.startswith("bag_type_"), StateFilter(ProductStates.waiting_for_bag_type))
async def process_bag_type(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора вида сумки"""
    bag_type = callback.data[9:]  # Убираем "bag_type_"

    # Находим название выбранного типа
    bag_params = get_bag_parameters()
    bag_type_params = bag_params.get('bag_type', {})
    selected_name = "Неизвестно"

    for value_name, value_code in bag_type_params.get('values', []):
        if value_code == bag_type:
            selected_name = value_name
            break

    await state.update_data(bag_type=bag_type, bag_type_name=selected_name)
    await state.set_state(ProductStates.waiting_for_bag_gender)

    user_name = callback.from_user.first_name
    await callback.message.edit_text(f"{user_name}, вид сумки: {selected_name}")
    await ask_bag_gender(callback.message, user_name)


async def ask_bag_gender(message: Message, user_name: str = ""):
    """Запрос для кого сумка"""
    bag_params = get_bag_parameters()
    gender_params = bag_params.get('bag_gender', {})

    builder = InlineKeyboardBuilder()

    for value_name, value_code in gender_params.get('values', []):
        builder.button(text=value_name, callback_data=f"bag_gender_{value_code}")

    builder.adjust(1)

    greeting = f"{user_name}, " if user_name else ""
    await message.answer(
        f"{greeting}выберите для кого сумка:",
        reply_markup=builder.as_markup()
    )


@router.callback_query(F.data.startswith("bag_gender_"), StateFilter(ProductStates.waiting_for_bag_gender))
async def process_bag_gender(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора для кого сумка"""
    bag_gender = callback.data[11:]  # Убираем "bag_gender_"

    # Находим название выбранного типа
    bag_params = get_bag_parameters()
    gender_params = bag_params.get('bag_gender', {})
    selected_name = "Неизвестно"

    for value_name, value_code in gender_params.get('values', []):
        if value_code == bag_gender:
            selected_name = value_name
            break

    await state.update_data(bag_gender=bag_gender, bag_gender_name=selected_name)

    user_name = callback.from_user.first_name
    await callback.message.edit_text(f"{user_name}, для кого: {selected_name}")

    # Переходим к стандартным параметрам (размер, состояние и т.д.)
    data = await state.get_data()
    category_name = data.get('category_name', '')

    needs_size = any(size_cat in category_name for size_cat in SIZE_CATEGORIES)

    if needs_size:
        await state.set_state(ProductStates.waiting_for_size)
        await ask_size(callback.message, user_name)
    else:
        await state.set_state(ProductStates.waiting_for_condition)
        await ask_condition(callback.message, user_name)

async def process_brand_success(message: Message, state: FSMContext, user_name: str):
    """Продолжение процесса после успешного выбора бренда с проверкой категории"""
    data = await state.get_data()
    brand = data.get('brand', '')
    category_name = data.get('category_name', '')

    # Проверяем, относится ли категория к сумкам
    if is_bag_category(category_name):
        # Если это сумка, запрашиваем дополнительные параметры
        await state.set_state(ProductStates.waiting_for_bag_type)
        await ask_bag_type(message, user_name)
    else:
        # Стандартный процесс для других категорий
        await process_standard_parameters(message, state, user_name)


async def process_standard_parameters(message: Message, state: FSMContext, user_name: str):
    """Стандартный процесс для категорий без дополнительных параметров"""
    data = await state.get_data()
    category_name = data.get('category_name', '')

    needs_size = any(size_cat in category_name for size_cat in SIZE_CATEGORIES)

    if needs_size:
        await state.set_state(ProductStates.waiting_for_size)
        await ask_size(message, user_name)
    else:
        await state.set_state(ProductStates.waiting_for_condition)
        await ask_condition(message, user_name)

@router.callback_query(F.data.startswith("exact_brand_"), StateFilter(ProductStates.waiting_for_brand))
async def process_exact_brand(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора точного бренда из похожих"""
    brand = callback.data[12:]  # Убираем "exact_brand_"

    await state.update_data(brand=brand)
    await callback.message.edit_text(f"✅ Бренд выбран: {brand}")
    await process_brand_success(callback.message, state, callback.from_user.first_name)
    await callback.answer()


@router.message(StateFilter(ProductStates.waiting_for_brand))
async def process_custom_brand(message: Message, state: FSMContext):
    """Обработка ручного ввода бренда"""
    brand = message.text.strip()
    if not brand:
        await message.answer("Бренд не может быть пустым. Введите название бренда:")
        return

    await state.update_data(brand=brand)

    # Проверяем, нужен ли размер для этой категории
    data = await state.get_data()
    category_name = data.get('category_name', '')

    needs_size = any(size_cat in category_name for size_cat in SIZE_CATEGORIES)

    user_name = message.from_user.first_name
    if needs_size:
        await state.set_state(ProductStates.waiting_for_size)
        await ask_size(message, user_name)
    else:
        await state.set_state(ProductStates.waiting_for_condition)
        await ask_condition(message, user_name)


# Обработчики для размера
@router.callback_query(F.data.startswith("size_"))
async def process_size(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора размера"""
    size_data = callback.data[5:]  # Убираем "size_"

    if size_data == "custom":
        await callback.message.edit_text("Введите размер товара:")
        await state.set_state(ProductStates.waiting_for_size)
        return

    if size_data == "skip":
        await state.update_data(size="")
    else:
        await state.update_data(size=size_data)

    user_name = callback.from_user.first_name
    size_text = size_data if size_data != "skip" else "не указан"

    await callback.message.edit_text(f"{user_name}, размер: {size_text}")
    await state.set_state(ProductStates.waiting_for_condition)
    await ask_condition(callback.message, user_name)


@router.message(StateFilter(ProductStates.waiting_for_size))
async def process_custom_size(message: Message, state: FSMContext):
    """Обработка ручного ввода размера"""
    size = message.text.strip()
    await state.update_data(size=size)

    user_name = message.from_user.first_name
    await message.answer(f"{user_name}, размер: {size}")
    await state.set_state(ProductStates.waiting_for_condition)
    await ask_condition(message, user_name)


# Обработчики для состояния товара
@router.callback_query(F.data.startswith("condition_"))
async def process_condition(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора состояния товара"""
    condition = callback.data[10:]  # Убираем "condition_"

    condition_names = {
        "new_with_tag": "новое с биркой",
        "excellent": "отличное",
        "good": "хорошее",
        "satisfactory": "удовлетворительное"
    }

    await state.update_data(condition=condition)
    await state.set_state(ProductStates.waiting_for_sale_type)

    user_name = callback.from_user.first_name
    condition_text = condition_names.get(condition, "не указано")

    await callback.message.edit_text(f"{user_name}, состояние: {condition_text}")
    await ask_sale_type(callback.message, user_name)


@router.callback_query(F.data.startswith("saletype_"))
async def process_sale_type(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора типа продажи"""
    sale_type = callback.data[9:]  # Убираем "saletype_"

    sale_type_names = {
        "resale": "товар приобретен на продажу",
        "manufacturer": "товар от производителя",
        "personal": "продаю своё"  # Добавляем название для нового типа
    }

    await state.update_data(sale_type=sale_type)
    await state.set_state(ProductStates.waiting_for_placement_type)

    user_name = callback.from_user.first_name
    sale_text = sale_type_names.get(sale_type, "не указан")

    await callback.message.edit_text(f"{user_name}, тип продажи: {sale_text}")
    await ask_placement_type(callback.message, user_name)


@router.callback_query(F.data.startswith("placement_"))
async def process_placement_type(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора типа размещения"""
    placement_type = callback.data[10:]  # Убираем "placement_"

    await state.update_data(placement_type=placement_type)

    user_name = callback.from_user.first_name

    if placement_type == "cities":
        # Размещение по городам - показываем методы для городов
        await state.set_state(ProductStates.waiting_for_placement_method)
        placement_text = "по городам"

        builder = InlineKeyboardBuilder()
        placement_methods = [
            ("📍 Указать точные города", "exact_cities"),
            ("📊 По количеству объявлений", "by_quantity"),
            ("🏢 Несколько объявлений в городе", "multiple_in_city")
        ]

        for method_name, method_code in placement_methods:
            builder.button(text=method_name, callback_data=f"method_{method_code}")

        builder.adjust(1)

        await callback.message.edit_text(
            f"{user_name}, размещение: {placement_text}\n\n"
            "Выберите вариант размещения:",
            reply_markup=builder.as_markup()
        )

    elif placement_type == "metro":
        # Размещение по метро - сразу переходим к выбору города метро
        await state.set_state(ProductStates.waiting_for_metro_city)
        placement_text = "по станциям метро"

        # Явно устанавливаем метод размещения
        await state.update_data(placement_method="metro")

        await callback.message.edit_text(f"{user_name}, размещение: {placement_text}")
        await ask_metro_city(callback.message, user_name)

    else:
        # Неизвестный тип размещения
        await callback.answer("Неизвестный тип размещения")


@router.callback_query(F.data.startswith("method_"))
async def process_placement_method(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора метода размещения"""
    method = callback.data[7:]  # Убираем "method_"

    # Явно сохраняем метод размещения
    await state.update_data(placement_method=method)
    user_name = callback.from_user.first_name

    if method == "exact_cities":
        # Поштучный ввод городов
        await state.set_state(ProductStates.waiting_for_city_input)
        await state.update_data(selected_cities=[])
        await callback.message.edit_text(f"{user_name}, выбран ввод точных городов.")
        await ask_city_input(callback.message, user_name)

    elif method == "by_quantity":
        # По количеству из XML
        await state.set_state(ProductStates.waiting_for_quantity)
        await callback.message.edit_text(f"{user_name}, выбран метод по количеству.")
        await ask_quantity_from_xml(callback.message, user_name)

    elif method == "multiple_in_city":
        # Несколько объявлений в одном городе
        await state.set_state(ProductStates.waiting_for_city_input)
        await state.update_data(
            selected_cities=[],
            placement_method="multiple_in_city"  # Явно указываем
        )
        await callback.message.edit_text(f"{user_name}, выбран метод мультиразмещения.")
        await ask_single_city_for_multiple(callback.message, user_name)

    elif method == "metro":  # Добавляем обработку метро
        await state.set_state(ProductStates.waiting_for_metro_city)
        await callback.message.edit_text(f"{user_name}, выбран метод размещения по станциям метро.")
        await ask_metro_city(callback.message, user_name)

    else:
        # Завершаем создание товара
        await complete_product_creation(callback.message, state, user_name)

@router.message(StateFilter(ProductStates.waiting_for_cities))
async def process_cities(message: Message, state: FSMContext):
    """Обработка ввода городов"""
    cities_text = message.text.strip()
    if not cities_text:
        await message.answer("Введите названия городов:")
        return

    cities = [city.strip() for city in cities_text.split(',')]
    await state.update_data(cities=cities)

    user_name = message.from_user.first_name
    await message.answer(f"{user_name}, города: {', '.join(cities)}")

    # Переходим к выбору даты старта вместо завершения
    await state.set_state(ProductStates.waiting_for_start_date)
    await ask_start_date(message, user_name)


# Обработчик для всех callback'ов календаря
@router.callback_query(CalendarCallback.filter())
async def handle_calendar_callback(
        callback: CallbackQuery,
        callback_data: CalendarCallback,
        state: FSMContext
):
    """Обработка всех callback'ов календаря"""
    current_state = await state.get_state()

    # Проверяем, что мы в правильном состоянии
    if current_state != ProductStates.waiting_for_start_date:
        await callback.answer("Неверное состояние для выбора даты")
        return

    calendar = ProductCalendar()
    selected, date = await calendar.process_selection(callback, callback_data)

    if selected:
        user_name = callback.from_user.first_name

        if date is None:
            # Пользователь выбрал "Пропустить"
            await state.update_data(start_date=None, start_time=None)
            await callback.message.answer(f"{user_name}, продажа начнется сразу после публикации.")
            await complete_product_creation(callback.message, state, user_name)
        else:
            # Сохраняем дату и переходим к выбору времени
            await state.update_data(start_date=date)
            await state.set_state(ProductStates.waiting_for_start_time)

            builder = InlineKeyboardBuilder()
            popular_times = [
                "09:00", "10:00", "11:00", "12:00",
                "13:00", "14:00", "15:00", "16:00",
                "17:00", "18:00", "19:00", "20:00"
            ]

            for time in popular_times:
                builder.button(text=time, callback_data=f"time_{time}")

            builder.button(text="✏️ Ввести вручную", callback_data="time_custom")
            builder.adjust(3)

            await callback.message.answer(
                f"{user_name}, дата начала продажи: {date.strftime('%d.%m.%Y')}\n\n"
                "⏰ Теперь выберите время начала продажи:",
                reply_markup=builder.as_markup()
            )


# Обновляем переход к запросу телефона
@router.callback_query(F.data.startswith("contact_"))
async def process_contact_method(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора способа связи"""
    contact_method = callback.data[8:]  # Убираем "contact_"

    contact_methods = {
        "both": "По телефону и в сообщении",
        "phone": "По телефону",
        "message": "В сообщениях"
    }

    method_name = contact_methods.get(contact_method, "Не указано")
    await state.update_data(contact_method=contact_method)

    user_name = callback.from_user.first_name
    await callback.message.edit_text(
        f"{user_name}, способ связи: {method_name}\n\n"
        "Теперь укажите номер телефона:"
    )

    await state.set_state(ProductStates.waiting_for_phone)
    await ask_phone_number(callback.message, user_name)

@router.callback_query(F.data.startswith("time_"), StateFilter(ProductStates.waiting_for_start_time))
async def process_time_selection(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора времени из кнопок"""
    time_data = callback.data[5:]  # Убираем "time_"

    if time_data == "custom":
        await callback.message.edit_text("Введите время в формате ЧЧ:ММ (например, 14:30):")
        return

    # Проверяем формат времени
    if not is_valid_time_format(time_data):
        await callback.answer("❌ Неверный формат времени", show_alert=True)
        return

    await process_time_input(callback.message, time_data, state, callback.from_user.first_name)


@router.message(StateFilter(ProductStates.waiting_for_start_time))
async def process_time_input_message(message: Message, state: FSMContext):
    """Обработка ручного ввода времени"""
    time_input = message.text.strip()

    if not is_valid_time_format(time_input):
        await message.answer(
            "❌ Неверный формат времени.\n\n"
            "Пожалуйста, введите время в формате ЧЧ:ММ (например, 14:30):"
        )
        return

    await process_time_input(message, time_input, state, message.from_user.first_name)


async def process_time_input(message: Message, time_str: str, state: FSMContext, user_name: str):
    """Обработка введенного времени"""
    # Получаем дату из состояния
    data = await state.get_data()
    start_date = data.get('start_date')

    if not start_date:
        await message.answer("❌ Ошибка: дата не найдена. Начните заново.")
        return

    # Собираем полную дату и время
    time_parts = time_str.split(':')
    hour = int(time_parts[0])
    minute = int(time_parts[1])

    full_datetime = start_date.replace(hour=hour, minute=minute, second=0, microsecond=0)

    await state.update_data(
        start_time=time_str,
        start_datetime=full_datetime
    )

    await message.answer(
        f"✅ Время установлено: {time_str}\n"
        f"📅 Полная дата начала: {full_datetime.strftime('%d.%m.%Y %H:%M')}"
    )

    # Завершаем создание товара
    await complete_product_creation(message, state, user_name)


def is_valid_time_format(time_str: str) -> bool:
    """Проверка корректности формата времени"""
    try:
        if not time_str or ':' not in time_str:
            return False

        parts = time_str.split(':')
        if len(parts) != 2:
            return False

        hour = int(parts[0])
        minute = int(parts[1])

        return 0 <= hour <= 23 and 0 <= minute <= 59

    except (ValueError, IndexError):
        return False