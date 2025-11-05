# bot/services/delivery_service.py
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext

from bot.handlers.base import StateManager
from bot.states import ProductStates


class DeliveryService:
    """Сервис для работы с доставкой"""

    # Список служб доставки со смайлами
    DELIVERY_SERVICES = [
        ("🔄 Выключена", "disabled"),
        ("📦 ПВЗ", "pickup"),
        ("🚚 Курьер", "courier"),
        ("📮 Постамат", "postamat"),
        ("🏢 Свой курьер", "own_courier"),
        ("🚛 Свой партнер СДЭК", "sdek"),
        ("🚚 Свой партнер Деловые Линии", "business_lines"),
        ("📦 Свой партнер DPD", "dpd"),
        ("🏭 Свой партнер ПЭК", "pek"),
        ("📮 Свой партнер Почта России", "russian_post"),
        ("🚀 Свой партнер СДЭК курьер", "sdek_courier"),
        ("🏪 Самовывоз с онлайн-оплатой", "self_pickup_online")
    ]

    @staticmethod
    async def ask_avito_delivery(message: Message, user_name: str = ""):
        """Запрос о доставке Авито"""
        builder = InlineKeyboardBuilder()

        builder.button(text="✅ Да, с доставкой Авито", callback_data="delivery_yes")
        builder.button(text="❌ Нет, без доставки", callback_data="delivery_no")
        builder.adjust(1)

        greeting = f"{user_name}, " if user_name else ""

        await message.answer(
            f"{greeting}нужна ли доставка через Авито?\n\n"
            "💡 Доставка Авито позволяет покупателям заказывать товары с доставкой по всей России.",
            reply_markup=builder.as_markup()
        )

    @staticmethod
    async def ask_delivery_services(message: Message, state: FSMContext, user_name: str = ""):
        """Запрос служб доставки"""
        builder = InlineKeyboardBuilder()

        data = await StateManager.get_data_safe(state)
        selected_services = data.get('delivery_services', [])

        for service_name, service_code in DeliveryService.DELIVERY_SERVICES:
            if service_code in selected_services:
                builder.button(text=f"✅ {service_name}", callback_data=f"service_{service_code}")
            else:
                builder.button(text=service_name, callback_data=f"service_{service_code}")

        builder.button(text="✅ Готово", callback_data="service_done")
        builder.adjust(1)

        greeting = f"{user_name}, " if user_name else ""

        await message.answer(
            f"{greeting}выберите службы доставки:\n\n"
            "💡 Можно выбрать несколько вариантов",
            reply_markup=builder.as_markup()
        )

    @staticmethod
    async def update_delivery_services_keyboard(message: Message, state: FSMContext, user_name: str = ""):
        """Обновление клавиатуры выбора служб доставки"""
        builder = InlineKeyboardBuilder()

        data = await StateManager.get_data_safe(state)
        selected_services = data.get('delivery_services', [])

        for service_name, service_code in DeliveryService.DELIVERY_SERVICES:
            if service_code in selected_services:
                builder.button(text=f"✅ {service_name}", callback_data=f"service_{service_code}")
            else:
                builder.button(text=service_name, callback_data=f"service_{service_code}")

        builder.button(text="✅ Готово", callback_data="service_done")
        builder.adjust(1)

        greeting = f"{user_name}, " if user_name else ""

        await message.edit_text(
            f"{greeting}выберите службы доставки:\n\n"
            f"📊 Выбрано: {len(selected_services)}\n"
            "💡 Можно выбрать несколько вариантов",
            reply_markup=builder.as_markup()
        )

    @staticmethod
    async def ask_delivery_discount(message: Message, user_name: str = ""):
        """Запрос скидки на доставку"""
        builder = InlineKeyboardBuilder()

        discount_options = [
            ("🎁 Бесплатная доставка", "free"),
            ("💰 Скидка на доставку", "discount"),
            ("🚫 Без скидки", "none")
        ]

        for discount_name, discount_code in discount_options:
            builder.button(text=discount_name, callback_data=f"discount_{discount_code}")

        builder.adjust(1)

        greeting = f"{user_name}, " if user_name else ""

        await message.answer(
            f"{greeting}укажите скидку на доставку:",
            reply_markup=builder.as_markup()
        )

    @staticmethod
    async def ask_delivery_discount_percent(message: Message, user_name: str = ""):
        """Запрос процента скидки на доставку"""
        greeting = f"{user_name}, " if user_name else ""

        await message.answer(
            f"{greeting}введите процент скидки на доставку (от 1 до 100):\n\n"
            "💡 Например: 10, 15, 20, 25 и т.д."
        )

    @staticmethod
    async def ask_multioffer(message: Message, user_name: str = ""):
        """Запрос о мультиобъявлении"""
        builder = InlineKeyboardBuilder()

        builder.button(text="✅ Да, мультиобъявление", callback_data="multioffer_yes")
        builder.button(text="❌ Нет, обычное объявление", callback_data="multioffer_no")
        builder.adjust(1)

        greeting = f"{user_name}, " if user_name else ""

        await message.answer(
            f"{greeting}является ли объявление мультиобъявлением?\n\n"
            "💡 Мультиобъявление позволяет разместить один товар в нескольких категориях или городах.",
            reply_markup=builder.as_markup()
        )