# bot/handlers/common_handlers.py
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove, Contact
from aiogram.filters import Command, StateFilter, CommandStart
from aiogram.fsm.context import FSMContext
import re

from bot.states import ProductStates
from bot.handlers.base import BaseHandler, StateManager
from bot.services.phone_service import PhoneService


class CommonHandlers(BaseHandler):
    """Общие обработчики"""

    def _register_handlers(self):
        # Обработка телефона
        self.router.message.register(
            self.process_contact_phone,
            StateFilter(ProductStates.waiting_for_phone),
            F.contact
        )
        self.router.message.register(
            self.process_manual_phone_input,
            StateFilter(ProductStates.waiting_for_phone),
            F.text == "✏️ Ввести вручную"
        )
        self.router.message.register(
            self.process_phone_message,
            StateFilter(ProductStates.waiting_for_phone)
        )

        # Обработка брендов
        self.router.callback_query.register(
            self.process_brand,
            F.data.startswith("brand_")
        )
        self.router.message.register(
            self.process_brand_input,
            StateFilter(ProductStates.waiting_for_brand)
        )
        self.router.callback_query.register(
            self.process_brand_retry,
            F.data == "br_retry",
            StateFilter(ProductStates.waiting_for_brand)
        )
        self.router.callback_query.register(
            self.process_exact_brand,
            F.data.startswith("exact_brand_"),
            StateFilter(ProductStates.waiting_for_brand)
        )

        # Обработка размера
        self.router.callback_query.register(
            self.process_size,
            F.data.startswith("size_")
        )
        self.router.message.register(
            self.process_custom_size,
            StateFilter(ProductStates.waiting_for_size)
        )

        # Обработка состояния товара
        self.router.callback_query.register(
            self.process_condition,
            F.data.startswith("condition_")
        )

        # Обработка типа продажи
        self.router.callback_query.register(
            self.process_sale_type,
            F.data.startswith("saletype_")
        )

        # Обработка типа размещения
        self.router.callback_query.register(
            self.process_placement_type,
            F.data.startswith("placement_")
        )

        # Обработка метода размещения
        self.router.callback_query.register(
            self.process_placement_method,
            F.data.startswith("method_")
        )

        # Обработка времени
        self.router.callback_query.register(
            self.process_time_selection,
            F.data.startswith("time_"),
            StateFilter(ProductStates.waiting_for_start_time)
        )
        self.router.message.register(
            self.process_time_input_message,
            StateFilter(ProductStates.waiting_for_start_time)
        )

        self.router.message.register(self.start_command, CommandStart())
        self.router.message.register(self.help_command, Command("help"))


    async def process_contact_phone(self, message: Message, state: FSMContext):
        """Обработка номера телефона из контакта"""
        contact = message.contact
        phone_number = contact.phone_number

        if not PhoneService.is_valid_phone(phone_number):
            await message.answer(
                "❌ Неверный формат номера телефона из контакта.\n"
                "Пожалуйста, введите номер вручную:",
                reply_markup=ReplyKeyboardRemove()
            )
            return

        normalized_phone = PhoneService.normalize_phone(phone_number)
        await StateManager.safe_update(
            state,
            contact_phone=normalized_phone,
            display_phone=phone_number
        )
        await state.set_state(ProductStates.waiting_for_contact_method)

        await message.answer(
            f"✅ Номер получен: {phone_number}",
            reply_markup=ReplyKeyboardRemove()
        )

        user_name = message.from_user.first_name
        from bot.services.product_service import ProductService
        await ProductService.show_contact_methods(message, user_name)

    async def process_manual_phone_input(self, message: Message, state: FSMContext):
        """Обработка выбора ручного ввода номера"""
        await message.answer(
            "Введите номер телефона вручную в одном из форматов:\n\n"
            "Корректные примеры:\n"
            "— +7 (495) 777-10-66\n"
            "— 8 905 207 04 90\n"
            "— 89052070490",
            reply_markup=ReplyKeyboardRemove()
        )

    async def process_phone_message(self, message: Message, state: FSMContext):
        """Обработка ручного ввода номера телефона"""
        phone = message.text.strip()

        if phone == "✏️ Ввести вручную":
            return

        if not PhoneService.is_valid_phone(phone):
            await message.answer(
                "❌ Неверный формат телефона. Пожалуйста, введите номер в одном из допустимых форматов:\n\n"
                "Корректные примеры:\n"
                "— +7 (495) 777-10-66\n"
                "— 8 905 207 04 90\n"
                "— 89052070490"
            )
            return

        normalized_phone = PhoneService.normalize_phone(phone)
        await StateManager.safe_update(
            state,
            contact_phone=normalized_phone,
            display_phone=phone
        )
        await state.set_state(ProductStates.waiting_for_contact_method)

        user_name = message.from_user.first_name
        await message.answer(f"✅ Номер подтвержден: {phone}")

        from bot.services.product_service import ProductService
        await ProductService.show_contact_methods(message, user_name)

    async def process_brand(self, callback: CallbackQuery, state: FSMContext):
        """Обработка выбора бренда"""
        brand_data = callback.data[6:]  # Убираем "brand_"

        if brand_data == "show_all":
            from bot.services.brand_service import BrandService
            brands = BrandService.load_brands()

            from aiogram.utils.keyboard import InlineKeyboardBuilder
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

        await StateManager.safe_update(state, brand=brand_data)
        await self._process_brand_success(callback.message, state, callback.from_user.first_name)

    async def process_brand_input(self, message: Message, state: FSMContext):
        """Обработка ручного ввода бренда"""
        brand_input = message.text.strip()

        if brand_input in ["✏️ Ввести другой бренд", "Ввести другой бренд"]:
            await message.answer("Введите название бренда:")
            return

        if not brand_input:
            await message.answer("Бренд не может быть пустым. Введите название бренда:")
            return

        from bot.services.brand_service import BrandService

        if BrandService.is_valid_brand(brand_input):
            await StateManager.safe_update(state, brand=brand_input)
            await self._process_brand_success(message, state, message.from_user.first_name)
            return

        similar_brands = BrandService.search_brands(brand_input)

        if similar_brands:
            from aiogram.utils.keyboard import InlineKeyboardBuilder
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

    async def process_brand_retry(self, callback: CallbackQuery, state: FSMContext):
        """Повторный ввод бренда"""
        await callback.message.edit_text("Введите название бренда:")
        await callback.answer()

    async def process_exact_brand(self, callback: CallbackQuery, state: FSMContext):
        """Обработка точного бренда из похожих"""
        brand = callback.data[12:]  # Убираем "exact_brand_"

        await StateManager.safe_update(state, brand=brand)
        await callback.message.edit_text(f"✅ Бренд выбран: {brand}")
        await self._process_brand_success(callback.message, state, callback.from_user.first_name)
        await callback.answer()

    async def _process_brand_success(self, message: Message, state: FSMContext, user_name: str):
        """Продолжение процесса после успешного выбора бренда"""
        data = await StateManager.get_data_safe(state)
        brand = data.get('brand', '')

        # Проверяем, нужен ли размер для этой категории
        category_name = data.get('category_name', '')
        needs_size = any(size_cat in category_name for size_cat in [
            "Мужская обувь", "Женская обувь", "Мужская одежда", "Женская одежда",
            "Брюки", "Джинсы", "Шорты", "Пиджаки и костюмы", "Рубашки", "Платья", "Юбки"
        ])

        await message.answer(f"✅ Бренд подтвержден: {brand}")

        if needs_size:
            await state.set_state(ProductStates.waiting_for_size)
            from bot.services.product_service import ProductService
            await ProductService.ask_size(message, user_name)
        else:
            await state.set_state(ProductStates.waiting_for_condition)
            from bot.services.product_service import ProductService
            await ProductService.ask_condition(message, user_name)

    async def process_size(self, callback: CallbackQuery, state: FSMContext):
        """Обработка выбора размера"""
        size_data = callback.data[5:]  # Убираем "size_"

        if size_data == "custom":
            await callback.message.edit_text("Введите размер товара:")
            await state.set_state(ProductStates.waiting_for_size)
            return

        if size_data == "skip":
            await StateManager.safe_update(state, size="")
        else:
            await StateManager.safe_update(state, size=size_data)

        user_name = callback.from_user.first_name
        size_text = size_data if size_data != "skip" else "не указан"

        await callback.message.edit_text(f"{user_name}, размер: {size_text}")
        await state.set_state(ProductStates.waiting_for_condition)

        from bot.services.product_service import ProductService
        await ProductService.ask_condition(callback.message, user_name)

    async def process_custom_size(self, message: Message, state: FSMContext):
        """Обработка ручного ввода размера"""
        size = message.text.strip()
        await StateManager.safe_update(state, size=size)

        user_name = message.from_user.first_name
        await message.answer(f"{user_name}, размер: {size}")
        await state.set_state(ProductStates.waiting_for_condition)

        from bot.services.product_service import ProductService
        await ProductService.ask_condition(message, user_name)

    async def process_condition(self, callback: CallbackQuery, state: FSMContext):
        """Обработка выбора состояния товара"""
        condition = callback.data[10:]  # Убираем "condition_"

        condition_names = {
            "new_with_tag": "новое с биркой",
            "excellent": "отличное",
            "good": "хорошее",
            "satisfactory": "удовлетворительное"
        }

        await StateManager.safe_update(state, condition=condition)
        await state.set_state(ProductStates.waiting_for_sale_type)

        user_name = callback.from_user.first_name
        condition_text = condition_names.get(condition, "не указано")

        await callback.message.edit_text(f"{user_name}, состояние: {condition_text}")

        from bot.services.product_service import ProductService
        await ProductService.ask_sale_type(callback.message, user_name)

    async def process_sale_type(self, callback: CallbackQuery, state: FSMContext):
        """Обработка выбора типа продажи"""
        sale_type = callback.data[9:]  # Убираем "saletype_"

        sale_type_names = {
            "resale": "товар приобретен на продажу",
            "manufacturer": "товар от производителя",
            "personal": "продаю своё"
        }

        await StateManager.safe_update(state, sale_type=sale_type)
        await state.set_state(ProductStates.waiting_for_placement_type)

        user_name = callback.from_user.first_name
        sale_text = sale_type_names.get(sale_type, "не указан")

        await callback.message.edit_text(f"{user_name}, тип продажи: {sale_text}")

        from bot.services.product_service import ProductService
        await ProductService.ask_placement_type(callback.message, user_name)

    async def process_placement_type(self, callback: CallbackQuery, state: FSMContext):
        """Обработка выбора типа размещения"""
        placement_type = callback.data[10:]  # Убираем "placement_"

        await StateManager.safe_update(state, placement_type=placement_type)

        user_name = callback.from_user.first_name

        if placement_type == "cities":
            await state.set_state(ProductStates.waiting_for_placement_method)

            from aiogram.utils.keyboard import InlineKeyboardBuilder
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
                f"{user_name}, размещение: по городам\n\n"
                "Выберите вариант размещения:",
                reply_markup=builder.as_markup()
            )

        elif placement_type == "metro":
            await state.set_state(ProductStates.waiting_for_metro_city)

            await callback.message.edit_text(f"{user_name}, размещение: по станциям метро")

            from bot.services.metro_service import MetroService
            await MetroService.ask_metro_city(callback.message, user_name)

    async def process_placement_method(self, callback: CallbackQuery, state: FSMContext):
        """Обработка выбора метода размещения"""
        method = callback.data[7:]  # Убираем "method_"

        await StateManager.safe_update(state, placement_method=method)
        user_name = callback.from_user.first_name

        if method == "exact_cities":
            await state.set_state(ProductStates.waiting_for_city_input)
            await StateManager.safe_update(state, selected_cities=[])

            await callback.message.edit_text(f"{user_name}, выбран ввод точных городов.")

            from bot.services.location_service import LocationService
            await LocationService.ask_city_input(callback.message, user_name)

        elif method == "by_quantity":
            await state.set_state(ProductStates.waiting_for_quantity)

            await callback.message.edit_text(f"{user_name}, выбран метод по количеству.")

            from bot.services.location_service import LocationService
            await LocationService.ask_quantity_from_xml(callback.message, user_name)

        elif method == "multiple_in_city":
            await state.set_state(ProductStates.waiting_for_city_input)
            await StateManager.safe_update(
                state,
                selected_cities=[],
                placement_method="multiple_in_city"
            )

            await callback.message.edit_text(f"{user_name}, выбран метод мультиразмещения.")

            from bot.services.location_service import LocationService
            await LocationService.ask_single_city_for_multiple(callback.message, user_name)

    async def process_time_selection(self, callback: CallbackQuery, state: FSMContext):
        """Обработка выбора времени из кнопок"""
        time_data = callback.data[5:]  # Убираем "time_"

        if time_data == "custom":
            await callback.message.edit_text("Введите время в формате ЧЧ:ММ (например, 14:30):")
            return

        if not self._is_valid_time_format(time_data):
            await callback.answer("❌ Неверный формат времени", show_alert=True)
            return

        await self._process_time_input(callback.message, time_data, state, callback.from_user.first_name)

    async def process_time_input_message(self, message: Message, state: FSMContext):
        """Обработка ручного ввода времени"""
        time_input = message.text.strip()

        if not self._is_valid_time_format(time_input):
            await message.answer(
                "❌ Неверный формат времени.\n\n"
                "Пожалуйста, введите время в формате ЧЧ:ММ (например, 14:30):"
            )
            return

        await self._process_time_input(message, time_input, state, message.from_user.first_name)

    async def _process_time_input(self, message: Message, time_str: str, state: FSMContext, user_name: str):
        """Обработка введенного времени"""
        data = await StateManager.get_data_safe(state)
        start_date = data.get('start_date')

        if not start_date:
            await message.answer("❌ Ошибка: дата не найдена. Начните заново.")
            return

        time_parts = time_str.split(':')
        hour = int(time_parts[0])
        minute = int(time_parts[1])

        full_datetime = start_date.replace(hour=hour, minute=minute, second=0, microsecond=0)

        await StateManager.safe_update(
            state,
            start_time=time_str,
            start_datetime=full_datetime
        )

        await message.answer(
            f"✅ Время установлено: {time_str}\n"
            f"📅 Полная дата начала: {full_datetime.strftime('%d.%m.%Y %H:%M')}"
        )

        from bot.services.product_service import ProductService
        await ProductService.complete_product_creation(message, state, user_name)

    def _is_valid_time_format(self, time_str: str) -> bool:
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

    async def start_command(self, message: Message):
        """Простой обработчик /start"""
        await message.answer(
            f"👋 Привет, {message.from_user.first_name}!\n\n"
            "🤖 Я бот для создания объявлений на Avito.\n\n"
            "🚀 Чтобы начать, используйте команду:\n"
            "<b>/new_product</b> - создать новый товар\n\n"
            "❓ Нужна помощь? Напишите <b>/help</b>"
        )

    async def help_command(self, message: Message):
        """Простой обработчик /help"""
        await message.answer(
            "📖 <b>Доступные команды:</b>\n\n"
            "🆕 /new_product - создать товар\n"
            "📋 /my_products - мои товары\n"
            "📦 /generate_xml - генерация XML\n"
            "🆘 /help - справка\n\n"
            "💡 Начните с команды /new_product!"
        )