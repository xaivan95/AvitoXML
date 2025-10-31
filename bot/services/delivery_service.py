# bot/services/delivery_service.py
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder


class DeliveryService:
    """Сервис для работы с доставкой"""

    DELIVERY_SERVICES = [
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

    @staticmethod
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

    @staticmethod
    async def ask_delivery_services(message: Message, state: FSMContext, user_name: str = ""):
        """Запрос выбора служб доставки"""
        from bot.handlers.base import StateManager

        data = await StateManager.get_data_safe(state)
        selected_services = data.get('delivery_services', [])

        builder = InlineKeyboardBuilder()

        for service_name, service_code in DeliveryService.DELIVERY_SERVICES:
            if service_code in selected_services:
                builder.button(text=f"✅ {service_name}", callback_data=f"service_{service_code}")
            else:
                builder.button(text=service_name, callback_data=f"service_{service_code}")

        builder.button(text="✅ Завершить выбор", callback_data="service_done")
        builder.adjust(1)

        selected_text = ", ".join([
            name for name, code in DeliveryService.DELIVERY_SERVICES
            if code in selected_services
        ])

        greeting = f"{user_name}, " if user_name else ""
        await message.answer(
            f"{greeting}выберите службы доставки (можно выбрать несколько):\n\n"
            f"📦 Выбрано: {selected_text or 'ничего'}\n\n"
            "💡 Нажимайте на кнопки для выбора/отмены выбора\n"
            "Когда закончите выбор, нажмите '✅ Завершить выбор'",
            reply_markup=builder.as_markup()
        )

    @staticmethod
    async def update_delivery_services_keyboard(message: Message, state: FSMContext, user_name: str = ""):
        """Обновление клавиатуры выбора служб доставки"""
        from bot.handlers.base import StateManager

        data = await StateManager.get_data_safe(state)
        selected_services = data.get('delivery_services', [])

        builder = InlineKeyboardBuilder()

        for service_name, service_code in DeliveryService.DELIVERY_SERVICES:
            if service_code in selected_services:
                builder.button(text=f"✅ {service_name}", callback_data=f"service_{service_code}")
            else:
                builder.button(text=service_name, callback_data=f"service_{service_code}")

        builder.button(text="✅ Завершить выбор", callback_data="service_done")
        builder.adjust(1)

        selected_text = ", ".join([
            name for name, code in DeliveryService.DELIVERY_SERVICES
            if code in selected_services
        ])

        greeting = f"{user_name}, " if user_name else ""
        await message.edit_text(
            f"{greeting}выберите службы доставки (можно выбрать несколько):\n\n"
            f"📦 Выбрано: {selected_text or 'ничего'}\n\n"
            "💡 Нажимайте на кнопки для выбора/отмены выбора\n"
            "Когда закончите выбор, нажмите '✅ Завершить выбор'",
            reply_markup=builder.as_markup()
        )

    @staticmethod
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
            "• 🆓 Бесплатная доставка\n"
            "• 💰 Скидка на доставку\n"
            "• 🚫 Нет скидки",
            reply_markup=builder.as_markup()
        )

    @staticmethod
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