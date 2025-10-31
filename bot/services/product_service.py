# bot/services/product_service.py
import uuid
from aiogram.types import Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from bot.calendar import ProductCalendar


class ProductService:
    """Сервис для работы с продуктами"""

    @staticmethod
    def generate_guid() -> str:
        """Генерация GUID для товара"""
        return str(uuid.uuid4())

    @staticmethod
    async def show_main_categories(message: Message, user_name: str = ""):
        """Показать основные категории"""
        import config

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

    @staticmethod
    async def show_subcategories(message: Message, category_id: str, user_name: str = ""):
        """Показать подкатегории"""
        import config

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

    @staticmethod
    def get_category_data(category_id: str):
        """Получить данные категории"""
        import config
        return config.AVITO_CATEGORIES.get(category_id)

    @staticmethod
    def process_subcategory_selection(main_category_id: str, subcategory_id: str):
        """Обработка выбора подкатегории"""
        import config

        category_data = config.AVITO_CATEGORIES.get(main_category_id)
        if not category_data:
            return None

        subcategories = category_data.get("subcategories", {})
        subcategory_name = subcategories.get(subcategory_id)

        if not subcategory_name:
            return None

        # Получаем ID категории для Avito
        avito_category_id = config.CATEGORY_IDS.get(
            subcategory_id,
            config.CATEGORY_IDS.get(main_category_id)
        )

        return {
            'category': avito_category_id,
            'category_name': f"{category_data['name']} - {subcategory_name}",
            'subcategory_name': subcategory_name
        }

    @staticmethod
    async def show_price_type_options(message: Message, user_name: str = ""):
        """Показать варианты цены"""
        builder = InlineKeyboardBuilder()

        builder.button(text="💰 Фиксированная цена", callback_data="price_fixed")
        builder.button(text="📊 Диапазон цен", callback_data="price_range")
        builder.button(text="⏩ Пропустить", callback_data="price_skip")
        builder.adjust(1)

        greeting = f"{user_name}, " if user_name else ""
        await message.answer(
            f"{greeting}укажите стоимость:\n\n"
            "1) 💰 Фиксированная цена\n"
            "2) 📊 Диапазон цен\n"
            "3) ⏩ Пропустить",
            reply_markup=builder.as_markup()
        )

    @staticmethod
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

    @staticmethod
    async def ask_phone_number(message: Message, user_name: str = ""):
        """Запрос номера телефона"""
        from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

        greeting = f"{user_name}, " if user_name else ""
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
            "• Нажать кнопку '📞 Поделиться номером'\n"
            "• Или ввести номер вручную",
            reply_markup=keyboard
        )

    @staticmethod
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

    @staticmethod
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

    @staticmethod
    async def ask_sale_type(message: Message, user_name: str = ""):
        """Запрос типа продажи"""
        builder = InlineKeyboardBuilder()

        sale_types = [
            ("🛒 Товар приобретен на продажу", "resale"),
            ("🏭 Товар от производителя", "manufacturer"),
            ("👤 Продаю своё", "personal")
        ]

        for sale_name, sale_code in sale_types:
            builder.button(text=sale_name, callback_data=f"saletype_{sale_code}")

        builder.adjust(1)

        greeting = f"{user_name}, " if user_name else ""
        await message.answer(
            f"{greeting}выберите тип продажи:",
            reply_markup=builder.as_markup()
        )

    @staticmethod
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

    @staticmethod
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

    @staticmethod
    async def complete_product_creation(message: Message, state, user_name: str = ""):
        """Завершение создания товара и сохранение в базу"""
        from bot.handlers.base import StateManager

        try:
            data = await StateManager.get_data_safe(state)

            # Проверяем обязательные поля
            required_fields = ['title', 'description', 'category', 'contact_phone']
            missing_fields = [field for field in required_fields if not data.get(field)]

            if missing_fields:
                await message.answer(f"Ошибка: не заполнены обязательные поля: {', '.join(missing_fields)}")
                return

            # Сохраняем товар в базу (если есть база данных)
            try:
                from bot.database import db
                await db.add_product(message.from_user.id, data)
                await db.clear_user_state(message.from_user.id)
            except Exception as e:
                print(f"Database error: {e}")
                # Продолжаем работу даже если база не доступна

            await state.clear()

            # Формируем статистику
            main_count = len(data.get('main_images', []))
            additional_count = len(data.get('additional_images', []))
            total_images = main_count + additional_count

            await message.answer(
                f"{user_name}, ✅ товар успешно добавлен!\n\n"
                f"📋 Статистика:\n"
                f"• Заголовок: {data['title'][:50]}...\n"
                f"• Описание: {len(data['description'])} символов\n"
                f"• Категория: {data.get('category_name', 'Не указана')}\n"
                f"• Основные фото: {main_count}\n"
                f"• Дополнительные фото: {additional_count}\n"
                f"• Всего фото: {total_images}\n\n"
                f"📊 Итог: создан товар с {total_images} фото\n\n"
                f"Используйте команды:\n"
                f"/new_product - добавить новый товар\n"
                f"/my_products - посмотреть все товары\n"
                f"/generate_xml - создать XML файл для Avito"
            )

        except Exception as e:
            print(f"Error in complete_product_creation: {e}")
            await message.answer(
                "❌ Произошла ошибка при сохранении товара. Попробуйте еще раз."
            )