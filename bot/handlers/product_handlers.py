# bot/handlers/product_handlers.py
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext

from bot.states import ProductStates
from bot.services.product_service import ProductService
from bot.services.location_service import LocationService
from bot.keyboards.builders import ProductKeyboards
from bot.handlers.base import BaseHandler, StateManager


class ProductHandlers(BaseHandler):
    """Обработчики для создания товара"""

    def _register_handlers(self):
        # Команды
        self.router.message.register(self.new_product_command, Command("new_product"))

        # Категории
        self.router.callback_query.register(self.process_main_category, F.data.startswith("cat_"))
        self.router.callback_query.register(self.process_subcategory, F.data.startswith("sub_"),
                                            StateFilter(ProductStates.waiting_for_subcategory))
        self.router.callback_query.register(self.process_subsubcategory, F.data.startswith("sub_"),
                                            StateFilter(ProductStates.waiting_for_subsubcategory))
        self.router.callback_query.register(self.back_to_categories, F.data == "back_categories")
        self.router.callback_query.register(self.back_to_subcategories, F.data.startswith("back_sub_"))

        # Основные данные товара
        self.router.message.register(self.process_product_title, StateFilter(ProductStates.waiting_for_title))
        self.router.message.register(self.process_product_description,
                                     StateFilter(ProductStates.waiting_for_description))

        # Цена
        self.router.callback_query.register(self.process_price_fixed, F.data == "price_fixed")
        self.router.callback_query.register(self.process_price_range, F.data == "price_range")
        self.router.callback_query.register(self.process_price_skip, F.data == "price_skip")
        self.router.message.register(self.process_fixed_price, StateFilter(ProductStates.waiting_for_price))
        self.router.message.register(self.process_price_range_input, StateFilter(ProductStates.waiting_for_price_range))

        # Контактные данные
        self.router.callback_query.register(self.process_contact_method, F.data.startswith("contact_"))

    async def new_product_command(self, message: Message, state: FSMContext):
        """Начало создания нового товара"""
        await state.clear()

        product_data = {
            'product_id': ProductService.generate_guid(),
            'main_images': [],
            'additional_images': [],
            'shuffle_images': False,
            'avito_delivery': False,
            'delivery_services': []
        }

        await StateManager.safe_update(state, **product_data)
        await state.set_state(ProductStates.waiting_for_category)

        await ProductService.show_main_categories(message, message.from_user.first_name)

    async def process_main_category(self, callback: CallbackQuery, state: FSMContext):
        """Обработка выбора основной категории"""
        category_id = callback.data[4:]
        category_data = ProductService.get_category_data(category_id)

        if not category_data:
            await callback.answer("Категория не найдена")
            return

        await StateManager.safe_update(
            state,
            main_category_id=category_id,
            main_category_name=category_data["name"]
        )
        await state.set_state(ProductStates.waiting_for_subcategory)

        await ProductService.show_subcategories(
            callback.message,
            category_id,
            callback.from_user.first_name
        )

    async def process_subcategory(self, callback: CallbackQuery, state: FSMContext):
        """Обработка выбора подкатегории ВТОРОГО уровня"""
        import config

        subcategory_id = callback.data[4:]
        print(f"DEBUG: Selected subcategory ID (2nd level): {subcategory_id}")

        data = await StateManager.get_data_safe(state)
        main_category_id = data.get('main_category_id')
        print(f"DEBUG: Main category ID: {main_category_id}")

        if not main_category_id:
            await callback.answer("Ошибка: основная категория не выбрана")
            return

        # Получаем информацию о подкатегории
        category_info = ProductService.process_subcategory_selection(main_category_id, subcategory_id)
        print(f"DEBUG: Category info: {category_info}")

        if not category_info:
            await callback.answer("Подкатегория не найдена")
            return

        if category_info.get('has_subcategories'):
            print(f"DEBUG: Has subcategories, showing subsubcategories")
            # Есть вложенные подкатегории - показываем их
            await state.set_state(ProductStates.waiting_for_subsubcategory)
            await ProductService.show_subsubcategories(callback.message, subcategory_id, callback.from_user.first_name)
        else:
            print(f"DEBUG: No subcategories, continuing process")
            # Проверяем, что все данные есть
            if not category_info.get('category_name') or 'None' in category_info.get('category_name', ''):
                # Если название некорректное, получаем его вручную
                subcategory_name = ProductService.get_subcategory_name(main_category_id, subcategory_id)
                category_info['category_name'] = f"{data.get('main_category_name')} - {subcategory_name}"
                category_info['subcategory_name'] = subcategory_name

            await StateManager.safe_update(state, **category_info)
            await state.set_state(ProductStates.waiting_for_title)

            await callback.message.edit_text(
                f"{callback.from_user.first_name}, ✅ категория выбрана: "
                f"{category_info['category_name']}\n\n"
                "Теперь введите заголовок объявления:"
            )

    async def process_subsubcategory(self, callback: CallbackQuery, state: FSMContext):
        """Обработка выбора подкатегории ТРЕТЬЕГО уровня"""
        import config

        subsubcategory_id = callback.data[4:]
        print(f"DEBUG: Selected subsubcategory ID (3rd level): {subsubcategory_id}")

        data = await StateManager.get_data_safe(state)
        main_category_id = data.get('main_category_id')

        if not main_category_id:
            await callback.answer("Ошибка: основная категория не выбрана")
            return

        # Пробуем найти подкатегорию третьего уровня
        category_info = ProductService.find_subsubcategory(main_category_id, subsubcategory_id)
        print(f"DEBUG: Subsubcategory info: {category_info}")

        if not category_info:
            # Если не нашли через специальный метод, пробуем через общий
            category_info = ProductService.process_subcategory_selection(main_category_id, subsubcategory_id)
            print(f"DEBUG: Subsubcategory info (fallback): {category_info}")

        if category_info:
            await StateManager.safe_update(state, **category_info)
            await state.set_state(ProductStates.waiting_for_title)

            await callback.message.edit_text(
                f"{callback.from_user.first_name}, ✅ категория выбрана: "
                f"{category_info['category_name']}\n\n"
                "Теперь введите заголовок объявления:"
            )
        else:
            # Отладочная информация
            print(
                f"DEBUG: Failed to find category info for main_category_id={main_category_id}, subsubcategory_id={subsubcategory_id}")
            ProductService.debug_category_structure(main_category_id, subsubcategory_id)
            await callback.answer("❌ Ошибка при выборе категории")

    async def back_to_categories(self, callback: CallbackQuery, state: FSMContext):
        """Возврат к выбору категорий"""
        await state.set_state(ProductStates.waiting_for_category)
        await ProductService.show_main_categories(
            callback.message,
            callback.from_user.first_name
        )

    async def back_to_subcategories(self, callback: CallbackQuery, state: FSMContext):
        """Возврат к подкатегориям из подкатегорий третьего уровня"""
        try:
            # Получаем ID родительской подкатегории из callback_data
            # Формат: "back_sub_52" где 52 - ID родительской подкатегории
            parent_subcategory_id = callback.data[10:]  # Убираем "back_sub_"

            # Находим основную категорию
            data = await StateManager.get_data_safe(state)
            main_category_id = data.get('main_category_id')

            if not main_category_id:
                await callback.message.edit_text("❌ Ошибка: основная категория не найдена")
                return

            # Показываем подкатегории снова
            await state.set_state(ProductStates.waiting_for_subcategory)
            await ProductService.show_subcategories(callback.message, main_category_id, callback.from_user.first_name)

            await callback.answer()

        except Exception as e:
            print(f"Error in back_to_subcategories: {e}")
            await callback.answer("❌ Ошибка при возврате к подкатегориям")

    async def process_product_title(self, message: Message, state: FSMContext):
        """Обработка заголовка товара"""
        title = message.text.strip()

        if not title:
            await message.answer("Заголовок не может быть пустым. Введите заголовок объявления:")
            return

        if len(title) > 100:
            await message.answer("Заголовок не должен превышать 100 символов. Введите более короткий заголовок:")
            return

        await StateManager.safe_update(state, title=title)
        await state.set_state(ProductStates.waiting_for_description)

        await message.answer(
            f"{message.from_user.first_name}, введите текст объявления, "
            "не менее 100 и не более 3500 символов:"
        )

    async def process_product_description(self, message: Message, state: FSMContext):
        """Обработка описания товара"""
        description = message.text.strip()

        if len(description) < 100:
            await message.answer(
                "Описание должно содержать не менее 100 символов. "
                "Пожалуйста, напишите более подробное описание:"
            )
            return

        if len(description) > 3500:
            await message.answer("Описание не должно превышать 3500 символов. Сократите текст и попробуйте снова:")
            return

        await StateManager.safe_update(state, description=description)
        await state.set_state(ProductStates.waiting_for_price_type)

        await ProductService.show_price_type_options(message, message.from_user.first_name)

    async def process_price_fixed(self, callback: CallbackQuery, state: FSMContext):
        """Обработка выбора фиксированной цены"""
        await StateManager.safe_update(state, price_type="fixed")
        await state.set_state(ProductStates.waiting_for_price)

        await callback.message.edit_text(
            f"{callback.from_user.first_name}, введите фиксированную цену в рублях (например: 2500):"
        )

    async def process_price_range(self, callback: CallbackQuery, state: FSMContext):
        """Обработка выбора диапазона цен"""
        await StateManager.safe_update(state, price_type="range")
        await state.set_state(ProductStates.waiting_for_price_range)

        await callback.message.edit_text(
            f"{callback.from_user.first_name}, введите диапазон цен в формате "
            "МИНИМУМ-МАКСИМУМ (например: 1200-1500):"
        )

    async def process_price_skip(self, callback: CallbackQuery, state: FSMContext):
        """Обработка пропуска цены"""
        await StateManager.safe_update(
            state,
            price_type="none",
            price=None,
            price_min=None,
            price_max=None
        )
        await state.set_state(ProductStates.waiting_for_phone)

        await callback.message.edit_text(
            f"{callback.from_user.first_name}, цена не будет указана в объявлении."
        )
        await ProductService.ask_phone_number(callback.message, callback.from_user.first_name)

    async def process_fixed_price(self, message: Message, state: FSMContext):
        """Обработка фиксированной цены"""
        try:
            price = int(message.text.strip())
            if price <= 0:
                await message.answer("Цена должна быть положительным числом. Введите цену еще раз:")
                return

            await StateManager.safe_update(state, price=price, price_min=None, price_max=None)
            await state.set_state(ProductStates.waiting_for_phone)

            await message.answer(f"✅ Цена установлена: {price} руб.")
            await ProductService.ask_phone_number(message, message.from_user.first_name)

        except ValueError:
            await message.answer("Цена должна быть числом. Введите цену еще раз:")

    async def process_price_range_input(self, message: Message, state: FSMContext):
        """Обработка диапазона цен"""
        text = message.text.strip()

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

            await StateManager.safe_update(state, price_min=min_price, price_max=max_price, price=None)
            await state.set_state(ProductStates.waiting_for_phone)

            await message.answer(f"✅ Диапазон цен установлен: {min_price}-{max_price} руб.")
            await ProductService.ask_phone_number(message, message.from_user.first_name)

        except ValueError:
            await message.answer("Цены должны быть числами. Введите диапазон в формате МИНИМУМ-МАКСИМУМ:")

    async def process_contact_method(self, callback: CallbackQuery, state: FSMContext):
        """Обработка выбора способа связи"""
        contact_method = callback.data[8:]

        contact_methods = {
            "both": "По телефону и в сообщении",
            "phone": "По телефону",
            "message": "В сообщениях"
        }

        method_name = contact_methods.get(contact_method, "Не указано")
        await StateManager.safe_update(state, contact_method=contact_method)
        await state.set_state(ProductStates.waiting_for_main_images)

        await callback.message.edit_text(
            f"{callback.from_user.first_name}, способ связи: {method_name}\n\n"
            "Теперь отправьте в этот чат ОСНОВНЫЕ фото объявления."
        )