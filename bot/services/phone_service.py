import re

from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from bot.calendar import ProductCalendar

class PhoneService:
    """Сервис для работы с телефонами"""

    @staticmethod
    def normalize_phone(phone: str) -> str:
        """Нормализация телефонного номера к формату +7XXXXXXXXXX"""
        cleaned = re.sub(r'[^\d+]', '', phone)

        if cleaned.startswith('8') and len(cleaned) == 11:
            cleaned = '+7' + cleaned[1:]
        elif cleaned.startswith('7') and len(cleaned) == 11:
            cleaned = '+' + cleaned
        elif len(cleaned) == 10:
            cleaned = '+7' + cleaned
        elif cleaned.startswith('+7') and len(cleaned) == 12:
            pass  # Уже в правильном формате

        return cleaned

    @staticmethod
    def is_valid_phone(phone: str) -> bool:
        """Проверка валидности телефонного номера"""
        normalized = PhoneService.normalize_phone(phone)

        if re.match(r'^(\+7|7|8)\d{10}$', normalized.replace('+', '').replace(' ', '')):
            return True

        patterns = [
            r'^\+7\s?\(\d{3}\)\s?\d{3}-\d{2}-\d{2}$',
            r'^8\s?\(\d{3}\)\s?\d{3}-\d{2}-\d{2}$',
            r'^8\s?\d{3}\s?\d{3}\s?\d{2}\s?\d{2}$',
            r'^\+7\s?\d{3}\s?\d{3}\s?\d{2}\s?\d{2}$',
        ]

        cleaned_phone = re.sub(r'[^\d]', '', phone)
        if len(cleaned_phone) in [10, 11]:
            return True

        for pattern in patterns:
            if re.match(pattern, phone.strip()):
                return True

        return False

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
    async def complete_product_creation(message: Message, state: FSMContext, user_name: str = ""):
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

            # Сохраняем товар в базу
            from bot.database import db
            await db.add_product(message.from_user.id, data)

            await state.clear()
            await db.clear_user_state(message.from_user.id)

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
