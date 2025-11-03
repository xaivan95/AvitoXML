# bot/handlers/location_handlers.py
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove, KeyboardButton, ReplyKeyboardMarkup
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.states import ProductStates
from bot.handlers.base import BaseHandler, StateManager
from bot.services.location_service import LocationService
from bot.services.metro_service import MetroService
from bot.keyboards.builders import KeyboardBuilder


class LocationHandlers(BaseHandler):
    """Обработчики для работы с локациями"""

    def _register_handlers(self):
        # Метро
        self.router.callback_query.register(
            self.process_metro_city,
            F.data.startswith("metro_city_"),
            StateFilter(ProductStates.waiting_for_metro_city)
        )
        self.router.message.register(
            self.process_metro_quantity,
            StateFilter(ProductStates.waiting_for_metro_quantity)
        )
        self.router.callback_query.register(
            self.back_to_placement_type,
            F.data == "back_to_placement_type",
            StateFilter(ProductStates.waiting_for_metro_city)
        )
        self.router.callback_query.register(
            self.back_to_metro_city,
            F.data == "back_to_metro_city",
            StateFilter(ProductStates.waiting_for_metro_quantity)
        )

        # Города
        self.router.message.register(
            self.handle_city_input,
            StateFilter(ProductStates.waiting_for_city_input)
        )
        self.router.message.register(
            self.process_single_city_input,
            StateFilter(ProductStates.waiting_for_city_input)
        )
        self.router.callback_query.register(
            self.confirm_city,
            F.data == "city_confirm",
            StateFilter(ProductStates.waiting_for_city_confirmation)
        )
        self.router.callback_query.register(
            self.reject_city,
            F.data == "city_reject",
            StateFilter(ProductStates.waiting_for_city_confirmation)
        )
        self.router.callback_query.register(
            self.restart_city_input,
            F.data == "cities_restart",
            StateFilter(ProductStates.waiting_for_city_input)
        )
        self.router.callback_query.register(
            self.skip_city_input,
            F.data == "cities_skip",
            StateFilter(ProductStates.waiting_for_city_input)
        )

        # Количество объявлений
        self.router.message.register(
            self.handle_quantity_input,
            StateFilter(ProductStates.waiting_for_quantity)
        )

        # Команды
        self.router.message.register(
            self.show_cities_status,
            Command("cities_status"),
            StateFilter(ProductStates.waiting_for_city_input)
        )

    async def process_metro_city(self, callback: CallbackQuery, state: FSMContext):
        """Обработка выбора города с метро"""
        city_name = callback.data[11:]  # Убираем "metro_city_"

        stations = MetroService.get_metro_stations(city_name)
        if not stations:
            await callback.answer("❌ В этом городе нет данных о станциях метро", show_alert=True)
            await MetroService.ask_metro_city(callback.message, callback.from_user.first_name)
            return

        await StateManager.safe_update(
            state,
            metro_city=city_name,
            metro_stations=stations,
            cities=[city_name],
            placement_method="metro"
        )
        await state.set_state(ProductStates.waiting_for_metro_quantity)

        user_name = callback.from_user.first_name
        sample_stations = ", ".join(stations[:5])

        await callback.message.edit_text(
            f"{user_name}, выбран город: 🚇 {city_name}\n\n"
            f"📍 Примеры станций: {sample_stations}...\n"
            f"📊 Всего станций: {len(stations)}\n\n"
            "Теперь введите количество объявлений:"
        )

    async def process_metro_quantity(self, message: Message, state: FSMContext):
        """Обработка количества объявлений для метро"""
        try:
            quantity = int(message.text.strip())

            if quantity <= 0:
                await message.answer("Количество должно быть положительным числом. Введите количество:")
                return

            if quantity > 100:
                await message.answer("Максимальное количество: 100. Введите меньшее число:")
                return

            data = await StateManager.get_data_safe(state)
            city_name = data.get('metro_city')
            all_stations = data.get('metro_stations', [])

            selected_stations = MetroService.get_random_stations(city_name, quantity)

            await StateManager.safe_update(
                state,
                quantity=quantity,
                selected_metro_stations=selected_stations,
                placement_method="metro"
            )

            user_name = message.from_user.first_name
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
            from bot.services.product_service import ProductService
            await ProductService.ask_start_date(message, user_name)

        except ValueError:
            await message.answer("Количество должно быть числом. Введите количество:")

    async def back_to_placement_type(self, callback: CallbackQuery, state: FSMContext):
        """Возврат к выбору типа размещения"""
        user_name = callback.from_user.first_name
        await state.set_state(ProductStates.waiting_for_placement_type)
        await callback.message.edit_text(f"{user_name}, возврат к выбору типа размещения.")

        from bot.services.product_service import ProductService
        await ProductService.ask_placement_type(callback.message, user_name)

    async def back_to_metro_city(self, callback: CallbackQuery, state: FSMContext):
        """Возврат к выбору города метро"""
        user_name = callback.from_user.first_name
        await state.set_state(ProductStates.waiting_for_metro_city)
        await callback.message.edit_text(f"{user_name}, возврат к выбору города.")
        await MetroService.ask_metro_city(callback.message, user_name)

    async def handle_city_input(self, message: Message, state: FSMContext):
        """Общий обработчик ввода городов"""
        data = await StateManager.get_data_safe(state)
        sale_type = data.get('sale_type')
        placement_method = data.get('placement_method')

        # Определяем тип: мультиобъявление или личная продажа
        is_multioffer = sale_type in ["resale", "manufacturer"]

        if not is_multioffer:
            # Личная продажа - один город
            await self._process_single_city_personal(message, state)
        else:
            # Мультиобъявление - логика в зависимости от метода
            if message.text == "✅ Завершить ввод городов":
                if placement_method in ["multiple_in_city", "exact_cities"]:
                    await self._finish_city_input(message, state)
                return

            if placement_method == "multiple_in_city":
                await self._process_single_city_for_multiple(message, state)
            elif placement_method == "exact_cities":
                await self._process_single_city_for_multiple(message, state)
            else:
                await self._process_single_city_personal(message, state)

    async def _process_single_city_personal(self, message: Message, state: FSMContext):
        """Обработка одного города для личной продажи"""
        city_name = message.text.strip()

        if not city_name:
            await message.answer("Введите название города:")
            return

        # Ищем город через Nominatim
        from нф import validate_city_nominatim
        result = await validate_city_nominatim(city_name)

        if result['valid']:
            city_data = result['data']

            selected_cities = [{
                'name': city_data['name'],
                'full_address': city_data['full_address'],
                'lat': city_data.get('lat'),
                'lon': city_data.get('lon'),
                'type': city_data.get('type')
            }]

            await StateManager.safe_update(
                state,
                selected_cities=selected_cities,
                cities=[city_data['name']],
                placement_method="single_city"
            )

            user_name = message.from_user.first_name
            await message.answer(
                f"✅ Город подтвержден!\n"
                f"🏙️ {city_data['name']}\n"
                f"📍 {city_data['full_address']}",
                reply_markup=ReplyKeyboardRemove()
            )

            # Сразу переходим к дате начала
            await state.set_state(ProductStates.waiting_for_start_date)
            from bot.services.product_service import ProductService
            await ProductService.ask_start_date(message, user_name)
        else:
            await message.answer(
                f"❌ Город '{city_name}' не найден.\n"
                "Попробуйте ввести другое название:"
            )

    async def _process_single_city_for_multiple(self, message: Message, state: FSMContext):
        """Обработка одного города для мультиразмещения"""
        city_name = message.text.strip()

        if not city_name:
            await message.answer("Введите название города:")
            return

        # Ищем город через Nominatim
        from нф import validate_city_nominatim
        result = await validate_city_nominatim(city_name)

        if result['valid']:
            city_data = result['data']

            selected_cities = [{
                'name': city_data['name'],
                'full_address': city_data['full_address'],
                'lat': city_data.get('lat'),
                'lon': city_data.get('lon'),
                'type': city_data.get('type')
            }]

            await StateManager.safe_update(
                state,
                selected_cities=selected_cities,
                cities=[city_data['name']]
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

    async def _process_city_input(self, message: Message, state: FSMContext):
        """Обработка ввода города"""
        city_name = message.text.strip()

        if not city_name:
            await message.answer("Введите название города:")
            return

        # Ищем город через Nominatim
        from нф import validate_city_nominatim
        result = await validate_city_nominatim(city_name)

        if result['valid']:
            city_data = result['data']
            await StateManager.safe_update(state, temp_city=city_data)

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

    async def process_single_city_input(self, message: Message, state: FSMContext):
        """Обработка ввода одного города (упрощенная версия)"""
        await self._process_city_input(message, state)

    async def confirm_city(self, callback: CallbackQuery, state: FSMContext):
        """Подтверждение города"""
        data = await StateManager.get_data_safe(state)
        city_data = data.get('temp_city')
        selected_cities = data.get('selected_cities', [])

        selected_cities.append({
            'name': city_data['name'],
            'full_address': city_data['full_address'],
            'lat': city_data.get('lat'),
            'lon': city_data.get('lon'),
            'type': city_data.get('type')
        })

        await StateManager.safe_update(state, selected_cities=selected_cities)
        await state.set_state(ProductStates.waiting_for_city_input)

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

        await callback.message.answer(
            "Можете продолжить ввод городов:",
            reply_markup=keyboard
        )

    async def reject_city(self, callback: CallbackQuery, state: FSMContext):
        """Отклонение города"""
        await state.set_state(ProductStates.waiting_for_city_input)
        await callback.message.edit_text("Введите другой город:")

    async def restart_city_input(self, callback: CallbackQuery, state: FSMContext):
        """Перезапуск ввода городов"""
        await StateManager.safe_update(state, selected_cities=[])
        await callback.message.edit_text("Введите название первого города:")
        await callback.answer()

    async def skip_city_input(self, callback: CallbackQuery, state: FSMContext):
        """Пропуск ввода городов"""
        await StateManager.safe_update(state, cities=[])
        await state.set_state(ProductStates.waiting_for_start_date)

        user_name = callback.from_user.first_name
        await callback.message.edit_text(f"{user_name}, размещение будет без привязки к городам.")

        from bot.services.product_service import ProductService
        await ProductService.ask_start_date(callback.message, user_name)

    async def _finish_city_input(self, message: Message, state: FSMContext):
        """Завершение ввода городов"""
        data = await StateManager.get_data_safe(state)
        selected_cities = data.get('selected_cities', [])

        if not selected_cities:
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

        city_names = [city['name'] for city in selected_cities]
        await StateManager.safe_update(state, cities=city_names)
        await state.set_state(ProductStates.waiting_for_start_date)

        user_name = message.from_user.first_name
        cities_list = ", ".join(city_names)

        await message.answer(
            f"{user_name}, ✅ завершен ввод городов!\n"
            f"🏙️ Добавлено городов: {len(selected_cities)}\n"
            f"📍 Список: {cities_list}",
            reply_markup=ReplyKeyboardRemove()
        )

        from bot.services.product_service import ProductService
        await ProductService.ask_start_date(message, user_name)

    async def handle_quantity_input(self, message: Message, state: FSMContext):
        """Общий обработчик количества"""
        data = await StateManager.get_data_safe(state)
        placement_method = data.get('placement_method')

        if placement_method == "multiple_in_city":
            await self._process_quantity_for_multiple(message, state)
        elif placement_method == "by_quantity":
            await self._process_quantity_from_xml(message, state)
        elif placement_method == "metro":
            await self.process_metro_quantity(message, state)
        else:
            await self._process_general_quantity(message, state)

    async def _process_quantity_for_multiple(self, message: Message, state: FSMContext):
        """Обработка количества для мультиразмещения"""
        try:
            quantity = int(message.text.strip())

            if quantity <= 0:
                await message.answer("Количество должно быть положительным числом. Введите количество:")
                return

            if quantity > 100:
                await message.answer("Максимальное количество: 100. Введите меньшее число:")
                return

            data = await StateManager.get_data_safe(state)
            selected_cities = data.get('selected_cities', [])

            if not selected_cities:
                await message.answer("❌ Ошибка: город не выбран. Пожалуйста, начните заново с выбора города.")
                return

            city_data = selected_cities[0]

            await StateManager.safe_update(
                state,
                quantity=quantity,
                cities=[city_data['name']],
                selected_cities=selected_cities
            )

            user_name = message.from_user.first_name
            await message.answer(
                f"{user_name}, ✅ настроено мультиразмещение:\n"
                f"🏙️ Город: {city_data['name']}\n"
                f"📊 Количество объявлений: {quantity}\n"
                f"📍 Будет сгенерировано {quantity} разных адресов"
            )

            await state.set_state(ProductStates.waiting_for_start_date)
            from bot.services.product_service import ProductService
            await ProductService.ask_start_date(message, user_name)

        except ValueError:
            await message.answer("Количество должно быть числом. Введите количество:")

    async def _process_quantity_from_xml(self, message: Message, state: FSMContext):
        """Обработка количества для метода из XML"""
        try:
            quantity = int(message.text.strip())
            cities = LocationService.load_cities_from_xml()

            if quantity <= 0:
                await message.answer("Количество должно быть положительным числом. Введите количество:")
                return

            if quantity > len(cities):
                await message.answer(f"Максимальное количество: {len(cities)}. Введите меньшее число:")
                return

            selected_cities = [city['name'] for city in cities[:quantity]]

            await StateManager.safe_update(
                state,
                cities=selected_cities,
                quantity=quantity
            )

            user_name = message.from_user.first_name
            cities_list = ", ".join(selected_cities)

            await message.answer(
                f"{user_name}, ✅ выбрано {quantity} городов:\n{cities_list}"
            )

            await state.set_state(ProductStates.waiting_for_start_date)
            from bot.services.product_service import ProductService
            await ProductService.ask_start_date(message, user_name)

        except ValueError:
            await message.answer("Количество должно быть числом. Введите количество:")

    async def _process_general_quantity(self, message: Message, state: FSMContext):
        """Обработка количества для общего случая"""
        try:
            quantity = int(message.text.strip())

            if quantity <= 0:
                await message.answer("Количество должно быть положительным числом. Введите количество:")
                return

            await StateManager.safe_update(state, quantity=quantity)

            user_name = message.from_user.first_name
            await message.answer(f"{user_name}, количество установлено: {quantity}")

            await state.set_state(ProductStates.waiting_for_start_date)
            from bot.services.product_service import ProductService
            await ProductService.ask_start_date(message, user_name)

        except ValueError:
            await message.answer("Количество должно быть числом. Введите количество:")

    async def show_cities_status(self, message: Message, state: FSMContext):
        """Показать текущий статус ввода городов"""
        data = await StateManager.get_data_safe(state)
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