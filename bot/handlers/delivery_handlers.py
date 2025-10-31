# bot/handlers/delivery_handlers.py
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from bot.states import ProductStates
from bot.handlers.base import BaseHandler, StateManager
from bot.services.delivery_service import DeliveryService


class DeliveryHandlers(BaseHandler):
    """Обработчики для работы с доставкой"""

    def _register_handlers(self):
        # Авито доставка
        self.router.callback_query.register(
            self.process_delivery_choice,
            F.data.startswith("delivery_")
        )

        # Службы доставки
        self.router.callback_query.register(
            self.process_delivery_service,
            F.data.startswith("service_")
        )

        # Скидка на доставку
        self.router.callback_query.register(
            self.process_delivery_discount,
            F.data.startswith("discount_")
        )

        # Мультиобъявление
        self.router.callback_query.register(
            self.process_multioffer,
            F.data.startswith("multioffer_")
        )

    async def process_delivery_choice(self, callback: CallbackQuery, state: FSMContext):
        """Обработка выбора Авито доставки"""
        delivery_choice = callback.data[9:]  # Убираем "delivery_"

        avito_delivery = (delivery_choice == "yes")
        await StateManager.safe_update(state, avito_delivery=avito_delivery)

        user_name = callback.from_user.first_name

        if avito_delivery:
            await state.set_state(ProductStates.waiting_for_delivery_services)
            await DeliveryService.ask_delivery_services(callback.message, state, user_name)
        else:
            await state.set_state(ProductStates.waiting_for_multioffer)
            await DeliveryService.ask_multioffer(callback.message, user_name)

    async def process_delivery_service(self, callback: CallbackQuery, state: FSMContext):
        """Обработка выбора службы доставки"""
        service_code = callback.data[8:]  # Убираем "service_"

        if service_code == "done":
            await state.set_state(ProductStates.waiting_for_delivery_discount)
            user_name = callback.from_user.first_name
            await DeliveryService.ask_delivery_discount(callback.message, user_name)
            return

        data = await StateManager.get_data_safe(state)
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

        await StateManager.safe_update(state, delivery_services=selected_services)
        await DeliveryService.update_delivery_services_keyboard(callback.message, state, callback.from_user.first_name)

    async def process_delivery_discount(self, callback: CallbackQuery, state: FSMContext):
        """Обработка выбора скидки на доставку"""
        discount_type = callback.data[9:]  # Убираем "discount_"

        discount_names = {
            "free": "бесплатная доставка",
            "discount": "скидка на доставку",
            "none": "нет скидки"
        }

        await StateManager.safe_update(state, delivery_discount=discount_type)
        await state.set_state(ProductStates.waiting_for_multioffer)

        user_name = callback.from_user.first_name
        discount_text = discount_names.get(discount_type, "не указано")

        await callback.message.edit_text(
            f"{user_name}, скидка на доставку: {discount_text}\n\n"
            "Теперь уточним тип объявления."
        )

        await DeliveryService.ask_multioffer(callback.message, user_name)

    async def process_multioffer(self, callback: CallbackQuery, state: FSMContext):
        """Обработка выбора мультиобъявления"""
        multioffer_choice = callback.data[11:]  # Убираем "multioffer_"

        multioffer = (multioffer_choice == "yes")
        await StateManager.safe_update(state, multioffer=multioffer)

        user_name = callback.from_user.first_name
        multioffer_text = "мультиобъявлением" if multioffer else "обычным объявлением"

        await callback.message.edit_text(
            f"{user_name}, объявление является {multioffer_text}.\n\n"
            "Теперь укажем дополнительные параметры."
        )

        await state.set_state(ProductStates.waiting_for_brand)
        from bot.services.brand_service import BrandService
        await BrandService.ask_brand_manual(callback.message, user_name)