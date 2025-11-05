# bot/handlers/product_handlers.py
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext

from bot.database import Database
from bot.states import ProductStates
from bot.services.product_service import ProductService
from bot.services.location_service import LocationService
from bot.keyboards.builders import ProductKeyboards
from bot.handlers.base import BaseHandler, StateManager


class ProductHandlers(BaseHandler):
    """Обработчики для создания товара"""
    def __init__(self, db: Database, bot: Bot = None):
        router = Router()
        super().__init__(router, db, bot)

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

        # Обработка размера одежды
        self.router.callback_query.register(
            self.process_clothing_size,
            F.data.startswith("clothing_size_"),
            StateFilter(ProductStates.waiting_for_clothing_size)
        )

        # Обработка цвета одежды
        self.router.callback_query.register(
            self.process_clothing_color,
            F.data.startswith("clothing_color_"),
            StateFilter(ProductStates.waiting_for_clothing_color)
        )

        # Обработка материала одежды
        self.router.callback_query.register(
            self.process_clothing_material,
            F.data.startswith("clothing_material_"),
            StateFilter(ProductStates.waiting_for_clothing_material)
        )

        # Обработка цвета от производителя для одежды
        self.router.message.register(
            self.process_clothing_manufacturer_color,
            StateFilter(ProductStates.waiting_for_clothing_manufacturer_color)
        )

    def _needs_full_clothing_properties(self, category_name: str) -> bool:
        """Проверяет, нужны ли полные свойства одежды (материал + размер + цвет)"""
        if not category_name:
            return False

        category_lower = category_name.lower()

        # Категории, для которых НЕ нужны полные свойства
        excluded_categories = [
            "нижнее бельё", "нижнее белье", "дублёнки", "дубленки", "шубы", "другое"
        ]

        return not any(excluded in category_lower for excluded in excluded_categories)

    async def _ask_clothing_size(self, message: Message, user_name: str):
        """Запрос размера одежды"""
        from aiogram.utils.keyboard import InlineKeyboardBuilder

        builder = InlineKeyboardBuilder()

        clothing_sizes = [
            "38 (XXS)", "40 (XS)", "42 (S)", "44 (S/M)", "46 (M)",
            "48 (L)", "50 (L/XL)", "52 (XL)", "54 (XXL)", "56 (3XL)",
            "58 (4XL)", "60 (5XL)", "62 (5XL)", "64 (6XL)", "66 (6XL)",
            "68 (7XL)", "70 (7XL)", "72 (8XL)", "74 (8XL)", "76 (8XL)",
            "78+ (8XL+)", "One size", "Без размера"
        ]

        for size in clothing_sizes:
            builder.button(text=size, callback_data=f"clothing_size_{size}")

        builder.adjust(2)

        await message.answer(
            f"{user_name}, выберите размер одежды:",
            reply_markup=builder.as_markup()
        )

    async def _ask_clothing_color(self, message: Message, user_name: str, can_skip: bool = False):
        """Запрос цвета одежды"""
        from aiogram.utils.keyboard import InlineKeyboardBuilder

        builder = InlineKeyboardBuilder()

        colors = [
            ("🔴 Красный", "red"),
            ("⚪ Белый", "white"),
            ("🎀 Розовый", "pink"),
            ("🍷 Бордовый", "burgundy"),
            ("🔵 Синий", "blue"),
            ("🟡 Жёлтый", "yellow"),
            ("💙 Голубой", "light_blue"),
            ("🟣 Фиолетовый", "purple"),
            ("🟠 Оранжевый", "orange"),
            ("🌈 Разноцветный", "multicolor"),
            ("⚫ Чёрный", "black"),
            ("🟤 Коричневый", "brown"),
            ("🟢 Зелёный", "green"),
            ("🔘 Серый", "gray"),
            ("🥚 Бежевый", "beige"),
            ("💿 Серебряный", "silver"),
            ("🌟 Золотой", "gold")
        ]

        for color_name, color_code in colors:
            builder.button(text=color_name, callback_data=f"clothing_color_{color_code}")

        if can_skip:
            builder.button(text="⏩ Пропустить", callback_data="clothing_color_skip")

        builder.adjust(3, 3, 3, 3, 3, 1)

        skip_note = "\n💡 Цвет можно пропустить" if can_skip else ""

        await message.answer(
            f"{user_name}, выберите цвет одежды:{skip_note}",
            reply_markup=builder.as_markup()
        )

    async def _ask_clothing_material(self, message: Message, user_name: str):
        """Запрос материала одежды"""
        materials = self._load_clothing_materials()

        from aiogram.utils.keyboard import InlineKeyboardBuilder
        builder = InlineKeyboardBuilder()

        for material in materials:
            builder.button(text=material, callback_data=f"clothing_material_{material}")

        builder.button(text="⏩ Пропустить", callback_data="clothing_material_skip")
        builder.adjust(2)

        await message.answer(
            f"{user_name}, выберите материал одежды:",
            reply_markup=builder.as_markup()
        )

    async def _ask_clothing_manufacturer_color(self, message: Message, user_name: str):
        """Запрос цвета от производителя для одежды"""
        await message.answer(
            f"{user_name}, введите цвет от производителя (например: 'угольный черный', 'кофе с молоком' и т.д.):\n\n"
            "💡 Это точное название цвета, указанное производителем. Можно пропустить, отправив любое сообщение."
        )

    def _load_clothing_materials(self):
        """Загрузка материалов для одежды"""
        try:
            import xml.etree.ElementTree as ET
            tree = ET.parse('materials.xml')
            root = tree.getroot()

            materials = []
            for material_elem in root.findall('.//MaterialsOdezhda'):
                materials.append(material_elem.text)

            return materials
        except Exception as e:
            print(f"Error loading materials from XML: {e}")
            # Возвращаем базовый список материалов
            return [
                "Хлопок", "Лён", "Шерсть", "Шёлк", "Кашемир", "Вискоза",
                "Полиэстер", "Нейлон", "Акрил", "Эластан", "Кожа", "Замша",
                "Джинса", "Флис", "Вельвет", "Бархат", "Атлас", "Сетка"
            ]

    async def process_clothing_size(self, callback: CallbackQuery, state: FSMContext):
            """Обработка выбора размера одежды"""
            size_data = callback.data[14:]  # Убираем "clothing_size_"

            await StateManager.safe_update(state, clothing_size=size_data)

            user_name = callback.from_user.first_name
            await callback.message.edit_text(f"{user_name}, размер одежды: {size_data}")

            # Определяем, нужно ли запрашивать материал
            data = await StateManager.get_data_safe(state)
            category_name = data.get('category_name', '')
            needs_full_properties = self._needs_full_clothing_properties(category_name)

            if needs_full_properties:
                # Запрашиваем материал
                await state.set_state(ProductStates.waiting_for_clothing_material)
                await self._ask_clothing_material(callback.message, user_name)
            else:
                # Пропускаем материал, переходим к цвету
                await StateManager.safe_update(state, clothing_material="")
                await state.set_state(ProductStates.waiting_for_clothing_color)

                # Для исключенных категорий цвет можно пропустить
                can_skip_color = not self._needs_full_clothing_properties(category_name)
                await self._ask_clothing_color(callback.message, user_name, can_skip=can_skip_color)

    async def process_clothing_material(self, callback: CallbackQuery, state: FSMContext):
            """Обработка выбора материала одежды"""
            material_data = callback.data[17:]  # Убираем "clothing_material_"

            if material_data == "skip":
                await StateManager.safe_update(state, clothing_material="")
                material_text = "не указан"
            else:
                await StateManager.safe_update(state, clothing_material=material_data)
                material_text = material_data

            user_name = callback.from_user.first_name
            await callback.message.edit_text(f"{user_name}, материал одежды: {material_text}")

            # Переходим к выбору цвета
            await state.set_state(ProductStates.waiting_for_clothing_color)

            data = await StateManager.get_data_safe(state)
            category_name = data.get('category_name', '')

            # Для полных свойств цвет обязателен, для исключенных - можно пропустить
            can_skip_color = not self._needs_full_clothing_properties(category_name)
            await self._ask_clothing_color(callback.message, user_name, can_skip=can_skip_color)

    async def process_clothing_color(self, callback: CallbackQuery, state: FSMContext):
            """Обработка выбора цвета одежды"""
            color_data = callback.data[15:]  # Убираем "clothing_color_"

            color_names = {
                "red": "Красный", "white": "Белый", "pink": "Розовый", "burgundy": "Бордовый",
                "blue": "Синий", "yellow": "Жёлтый", "light_blue": "Голубой", "purple": "Фиолетовый",
                "orange": "Оранжевый", "multicolor": "Разноцветный", "gray": "Серый", "beige": "Бежевый",
                "black": "Чёрный", "brown": "Коричневый", "green": "Зелёный", "silver": "Серебряный",
                "gold": "Золотой", "skip": "Пропустить"
            }

            if color_data == "skip":
                await StateManager.safe_update(state, clothing_color="")
                color_text = "не указан"
            else:
                await StateManager.safe_update(state, clothing_color=color_data)
                color_text = color_names.get(color_data, color_data)

            user_name = callback.from_user.first_name
            await callback.message.edit_text(f"{user_name}, цвет одежды: {color_text}")

            # Переходим к вводу цвета от производителя
            await state.set_state(ProductStates.waiting_for_clothing_manufacturer_color)
            await self._ask_clothing_manufacturer_color(callback.message, user_name)

    async def process_clothing_manufacturer_color(self, message: Message, state: FSMContext):
            """Обработка ввода цвета от производителя для одежды"""
            manufacturer_color = message.text.strip()

            await StateManager.safe_update(state, clothing_manufacturer_color=manufacturer_color)

            user_name = message.from_user.first_name
            if manufacturer_color:
                await message.answer(f"{user_name}, цвет от производителя: {manufacturer_color}")
            else:
                await message.answer(f"{user_name}, цвет от производителя не указан")

            # Продолжаем процесс - переходим к состоянию товара
            await state.set_state(ProductStates.waiting_for_condition)
            from bot.services.product_service import ProductService
            await ProductService.ask_condition(message, user_name)

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

            # ВСЕГДА сначала запрашиваем заголовок, потом дополнительные свойства
            await state.set_state(ProductStates.waiting_for_title)
            await self._ask_product_title(callback.message, callback.from_user.first_name)

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

            # ВСЕГДА сначала запрашиваем заголовок, потом дополнительные свойства
            await state.set_state(ProductStates.waiting_for_title)
            await self._ask_product_title(callback.message, callback.from_user.first_name)
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

    async def _ask_product_title(self, message: Message, user_name: str):
        """Запрос заголовка товара"""
        await message.answer(
            f"{user_name}, введите заголовок объявления (максимум 100 символов):"
        )

    async def process_product_title(self, message: Message, state: FSMContext):
        """Обработка заголовка товара"""
        title = message.text.strip()

        if not title:
            await message.answer("Заголовок не может быть пустым. Введите заголовок объявления:")
            return

        if len(title) > 50:
            await message.answer("Заголовок не должен превышать 50 символов. Введите более короткий заголовок:")
            return

        await StateManager.safe_update(state, title=title)
        await state.set_state(ProductStates.waiting_for_description)

        await message.answer(
            f"{message.from_user.first_name}, введите текст объявления, "
            "не менее 100 и не более 7500 символов:"
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

        if len(description) > 7500:
            await message.answer("Описание не должно превышать 7500 символов. Сократите текст и попробуйте снова:")
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