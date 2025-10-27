from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
import re
import random
import uuid
from datetime import datetime

from bot.database import db
from bot.states import ProductStates
import config
import xml.etree.ElementTree as ET
from typing import List

def load_brands() -> List[str]:
    """Загрузка брендов из XML файла"""
    try:
        tree = ET.parse('brands.xml')
        root = tree.getroot()
        brands = [brand.text for brand in root.findall('brand') if brand.text]
        return brands
    except Exception as e:
        print(f"Error loading brands: {e}")
        return ["Nike", "Adidas", "Reebok", "Puma", "No name", "Другой бренд"]


# Категории, требующие размер
SIZE_CATEGORIES = [
    "Мужская обувь", "Женская обувь", "Мужская одежда", "Женская одежда",
    "Брюки", "Джинсы", "Шорты", "Пиджаки и костюмы", "Рубашки", "Платья", "Юбки"
]


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
        ("🏭 Товар от производителя", "manufacturer")
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


async def ask_additional_images(message: Message, user_name: str = ""):
    """Запрос дополнительных изображений"""
    greeting = f"{user_name}, " if user_name else ""
    await message.answer(
        f"{greeting}теперь отправьте ДОПОЛНИТЕЛЬНЫЕ фотографии объявления.\n\n"
        "📸 Вы можете отправлять фото по одному или несколькими сообщениями.\n"
        "После отправки всех дополнительных фото нажмите /finish_additional_images\n\n"
        "Если дополнительных фото нет, просто нажмите /finish_additional_images"
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

        # Объединяем ВСЕ изображения (основные + дополнительные)
        main_images = data.get('main_images', [])
        additional_images = data.get('additional_images', [])
        all_images = main_images + additional_images

        # Перемешиваем если нужно
        if data.get('shuffle_images', False) and all_images:
            random.shuffle(all_images)

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
            'placement_type': data.get('placement_type', ''),
            'placement_method': data.get('placement_method', ''),
            'cities': data.get('cities', []),
            'quantity': data.get('quantity', 1)
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
            "manufacturer": "🏭 Товар от производителя"
        }

        await message.answer(
            f"{user_name}, ✅ товар успешно добавлен!\n\n"
            f"📋 Статистика:\n"
            f"• Заголовок: {data['title'][:50]}...\n"
            f"• Категория: {data.get('category_name', 'Не указана')}\n"
            f"• Бренд: {data.get('brand', 'Не указан')}\n"
            f"• Размер: {data.get('size', 'Не указан')}\n"
            f"• Состояние: {condition_names.get(data.get('condition', ''), 'Не указано')}\n"
            f"• Тип продажи: {sale_type_names.get(data.get('sale_type', ''), 'Не указан')}\n"
            f"• Основные фото: {main_count}\n"
            f"• Дополнительные фото: {additional_count}\n"
            f"• Всего фото: {len(all_images)}\n"
            f"• Перемешивание: {'Да' if data.get('shuffle_images') else 'Нет'}\n"
            f"• Доставка: {delivery_text}\n"
            f"• Скидка на доставку: {discount_names.get(delivery_discount, 'Не указано')}\n"
            f"• Мультиобъявление: {'Да' if multioffer else 'Нет'}\n\n"
            f"Используйте команды:\n"
            f"/new_product - добавить новый товар\n"
            f"/my_products - посмотреть все товары\n"
            f"/generate_xml - создать XML файл"
        )

    except Exception as e:
        print(f"Error in complete_product_creation: {e}")
        await message.answer("Произошла ошибка при сохранении товара. Попробуйте еще раз.")

# ========== ОСНОВНЫЕ ОБРАБОТЧИКИ ==========

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
        f"{user_name}, цена не будет указана в объявлении.\n\n"
        "Теперь укажите контактный номер телефона в одном из допустимых форматов.\n"
        "Корректные примеры:\n"
        "— +7 (495) 777-10-66\n"
        "— (81374) 4-55-75\n"
        "— 8 905 207 04 90\n"
        "— +7 905 2070490\n"
        "— 88123855085"
    )


@router.message(StateFilter(ProductStates.waiting_for_price))
async def process_fixed_price(message: Message, state: FSMContext):
    """Обработка фиксированной цены"""
    try:
        price = int(message.text.strip())
        if price <= 0:
            await message.answer("Цена должна быть положительным числом. Введите цену еще раз:")
            return

        await state.update_data(price=price, price_min=None, price_max=None)
        await state.set_state(ProductStates.waiting_for_phone)

        user_name = message.from_user.first_name
        await message.answer(
            f"{user_name}, цена установлена: {price} руб.\n\n"
            "Теперь укажите контактный номер телефона в одном из допустимых форматов.\n"
            "Корректные примеры:\n"
            "— +7 (495) 777-10-66\n"
            "— (81374) 4-55-75\n"
            "— 8 905 207 04 90\n"
            "— +7 905 2070490\n"
            "— 88123855085"
        )
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
        await message.answer(
            f"{user_name}, диапазон цен установлен: {min_price}-{max_price} руб.\n\n"
            "Теперь укажите контактный номер телефона в одном из допустимых форматов.\n"
            "Корректные примеры:\n"
            "— +7 (495) 777-10-66\n"
            "— (81374) 4-55-75\n"
            "— 8 905 207 04 90\n"
            "— +7 905 2070490\n"
            "— 88123855085"
        )
    except ValueError:
        await message.answer(
            "Цены должны быть числами. Введите диапазон в формате МИНИМУМ-МАКСИМУМ (например: 1200-1500):")


def normalize_phone(phone: str) -> str:
    """Нормализация телефонного номера к формату +7XXXXXXXXXX"""
    # Удаляем все нецифровые символы, кроме +
    cleaned = re.sub(r'[^\d+]', '', phone)

    # Если номер начинается с 8, заменяем на +7
    if cleaned.startswith('8'):
        cleaned = '+7' + cleaned[1:]
    # Если номер начинается с 7, добавляем +
    elif cleaned.startswith('7'):
        cleaned = '+' + cleaned
    # Если номер начинается без кода страны, добавляем +7
    elif len(cleaned) == 10:
        cleaned = '+7' + cleaned

    return cleaned


def is_valid_phone(phone: str) -> bool:
    """Проверка валидности телефонного номера"""
    normalized = normalize_phone(phone)

    # Проверяем формат +7XXXXXXXXXX (11 цифр после +7)
    if re.match(r'^\+7\d{10}$', normalized):
        return True

    # Проверяем российские номера без международного формата
    if re.match(r'^8\d{10}$', phone.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')):
        return True

    # Проверяем другие форматы
    patterns = [
        r'^\+7\s?\(\d{3}\)\s?\d{3}-\d{2}-\d{2}$',
        r'^\(\d{5}\)\s?\d-\d{2}-\d{2}$',
        r'^8\s?\d{3}\s?\d{3}\s?\d{2}\s?\d{2}$',
        r'^\+7\s?\d{3}\s?\d{7}$',
        r'^\d{11}$'
    ]

    for pattern in patterns:
        if re.match(pattern, phone.strip()):
            return True

    return False


@router.message(StateFilter(ProductStates.waiting_for_phone))
async def process_phone(message: Message, state: FSMContext):
    """Обработка телефонного номера"""
    phone = message.text.strip()

    if not is_valid_phone(phone):
        await message.answer(
            "Неверный формат телефона. Пожалуйста, введите номер в одном из допустимых форматов:\n\n"
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
        # Это часть альбома, обрабатывается в process_main_album_images
        return

    # Одиночное фото
    largest_photo = message.photo[-1]
    photo_file_id = largest_photo.file_id

    await state.update_data(main_images=[photo_file_id])

    user_name = message.from_user.first_name
    await message.answer(
        f"{user_name}, ✅ получено 1 основное изображение!\n\n"
        "Теперь переходим к дополнительным фотографиям."
    )

    await state.set_state(ProductStates.waiting_for_additional_images)
    await ask_additional_images(message, user_name)


@router.message(Command("finish_main_images"))
async def finish_main_images_command(message: Message, state: FSMContext):
    """Завершение добавления основных изображений"""
    data = await state.get_data()

    # Проверяем, есть ли изображения в временном хранилище
    user_albums = [album for album in temp_main_albums.values() if album['user_id'] == message.from_user.id]

    main_images = data.get('main_images', [])

    if user_albums:
        # Добавляем фото из всех альбомов пользователя
        for album in user_albums:
            main_images.extend(album['photos'])

        # Удаляем обработанные альбомы
        for media_group_id, album in list(temp_main_albums.items()):
            if album['user_id'] == message.from_user.id:
                del temp_main_albums[media_group_id]

    # Сохраняем основные изображения
    await state.update_data(main_images=main_images)
    await state.set_state(ProductStates.waiting_for_additional_images)

    user_name = message.from_user.first_name
    if main_images:
        await message.answer(
            f"{user_name}, ✅ получено {len(main_images)} основных изображений!\n\n"
            "Теперь переходим к дополнительным фотографиям."
        )
    else:
        await message.answer(
            f"{user_name}, основных изображений нет. Переходим к дополнительным фотографиям."
        )

    await ask_additional_images(message, user_name)


# Обработка дополнительных изображений
@router.message(StateFilter(ProductStates.waiting_for_additional_images), F.media_group_id)
async def process_additional_album_images(message: Message, state: FSMContext):
    """Обработка альбома дополнительных изображений"""
    media_group_id = message.media_group_id

    if media_group_id not in temp_additional_albums:
        temp_additional_albums[media_group_id] = {
            'user_id': message.from_user.id,
            'photos': [],
            'created_at': datetime.now()
        }

    # Добавляем фото в альбом
    if message.photo:
        # Берем самое большое фото
        largest_photo = message.photo[-1]
        temp_additional_albums[media_group_id]['photos'].append(largest_photo.file_id)


@router.message(StateFilter(ProductStates.waiting_for_additional_images), F.photo)
async def process_additional_single_image(message: Message, state: FSMContext):
    """Обработка одиночного дополнительного изображения"""
    if message.media_group_id:
        # Это часть альбома, обрабатывается в process_additional_album_images
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


@router.message(Command("finish_additional_images"))
async def finish_additional_images_command(message: Message, state: FSMContext):
    """Завершение добавления дополнительных изображений"""
    data = await state.get_data()

    # Проверяем, есть ли изображения в временном хранилище
    user_albums = [album for album in temp_additional_albums.values() if album['user_id'] == message.from_user.id]

    additional_images = data.get('additional_images', [])

    if user_albums:
        # Добавляем фото из всех альбомов пользователя
        for album in user_albums:
            additional_images.extend(album['photos'])

        # Удаляем обработанные альбомы
        for media_group_id, album in list(temp_additional_albums.items()):
            if album['user_id'] == message.from_user.id:
                del temp_additional_albums[media_group_id]

    await state.update_data(additional_images=additional_images)
    await state.set_state(ProductStates.waiting_for_shuffle_images)

    user_name = message.from_user.first_name
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

    # Переходим к выбору бренда
    await state.set_state(ProductStates.waiting_for_brand)
    await ask_brand(callback.message, user_name)


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


# Обработчики для типа продажи
@router.callback_query(F.data.startswith("saletype_"))
async def process_sale_type(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора типа продажи"""
    sale_type = callback.data[9:]  # Убираем "saletype_"

    sale_type_names = {
        "resale": "товар приобретен на продажу",
        "manufacturer": "товар от производителя"
    }

    await state.update_data(sale_type=sale_type)
    await state.set_state(ProductStates.waiting_for_placement_type)

    user_name = callback.from_user.first_name
    sale_text = sale_type_names.get(sale_type, "не указан")

    await callback.message.edit_text(f"{user_name}, тип продажи: {sale_text}")
    await ask_placement_type(callback.message, user_name)


# Обработчики для типа размещения
@router.callback_query(F.data.startswith("placement_"))
async def process_placement_type(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора типа размещения"""
    placement_type = callback.data[10:]  # Убираем "placement_"

    await state.update_data(placement_type=placement_type)
    await state.set_state(ProductStates.waiting_for_placement_method)

    user_name = callback.from_user.first_name
    placement_text = "по городам" if placement_type == "cities" else "по станциям метро"

    await callback.message.edit_text(f"{user_name}, размещение: {placement_text}")
    await ask_placement_method(callback.message, user_name)


# Обработчики для метода размещения
@router.callback_query(F.data.startswith("method_"))
async def process_placement_method(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора метода размещения"""
    method = callback.data[7:]  # Убираем "method_"

    await state.update_data(placement_method=method)

    user_name = callback.from_user.first_name

    if method == "exact_cities":
        await state.set_state(ProductStates.waiting_for_cities)
        await ask_cities(callback.message, user_name)
    elif method in ["by_quantity", "multiple_in_city"]:
        await state.set_state(ProductStates.waiting_for_quantity)
        await ask_quantity(callback.message, user_name)
    else:
        # Завершаем создание товара
        await complete_product_creation(callback.message, state, user_name)


# Обработчики для городов
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

    # Завершаем создание товара
    await complete_product_creation(message, state, user_name)


# Обработчики для количества
@router.message(StateFilter(ProductStates.waiting_for_quantity))
async def process_quantity(message: Message, state: FSMContext):
    """Обработка ввода количества"""
    try:
        quantity = int(message.text.strip())
        if quantity <= 0:
            await message.answer("Количество должно быть положительным числом. Введите количество:")
            return

        await state.update_data(quantity=quantity)

        user_name = message.from_user.first_name
        await message.answer(f"{user_name}, количество объявлений: {quantity}")

        # Завершаем создание товара
        await complete_product_creation(message, state, user_name)

    except ValueError:
        await message.answer("Количество должно быть числом. Введите количество:")


