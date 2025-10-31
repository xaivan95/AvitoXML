# bot/handlers/common_handlers.py
import os
from datetime import datetime
import xml.etree.ElementTree as ET
from random import random
from xml.dom import minidom

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove, Contact, BufferedInputFile
from aiogram.filters import Command, StateFilter, CommandStart
from aiogram.fsm.context import FSMContext
import re

from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.calendar import CalendarCallback, ProductCalendar
from bot.services.product_service import ProductService
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

        self.router.callback_query.register(
            self.handle_calendar_callback,
            CalendarCallback.filter()
        )

        self.router.message.register(
            self.my_products_command,
            Command("my_products")
        )
        self.router.message.register(
            self.generate_xml_command,
            Command("generate_xml")
        )
        self.router.callback_query.register(
            self.process_bag_type,
            F.data.startswith("bag_type_")
        )

        # Обработка назначения сумки (для кого)
        self.router.callback_query.register(
            self.process_bag_gender,
            F.data.startswith("bag_gender_")
        )

        # Обработка цвета сумки
        self.router.callback_query.register(
            self.process_bag_color,
            F.data.startswith("bag_color_"),
            StateFilter(ProductStates.waiting_for_bag_color)
        )

        # Обработка материала сумки
        self.router.callback_query.register(
            self.process_bag_material,
            F.data.startswith("bag_material_"),
            StateFilter(ProductStates.waiting_for_bag_material)
        )

    async def process_bag_color(self, callback: CallbackQuery, state: FSMContext):
        """Обработка выбора цвета сумки/рюкзака"""
        try:
            color_data = callback.data[10:]  # Убираем "bag_color_"

            color_names = {
                "red": "Красный", "white": "Белый", "pink": "Розовый", "burgundy": "Бордовый",
                "blue": "Синий", "yellow": "Жёлтый", "light_blue": "Голубой", "purple": "Фиолетовый",
                "orange": "Оранжевый", "multicolor": "Разноцветный", "gray": "Серый", "beige": "Бежевый",
                "black": "Чёрный", "brown": "Коричневый", "green": "Зелёный", "silver": "Серебряный",
                "gold": "Золотой", "skip": "Пропустить"
            }

            if color_data not in color_names:
                await callback.answer("❌ Неизвестный цвет")
                return

            if color_data == "skip":
                await StateManager.safe_update(state, bag_color="")
                color_text = "не указан"
            else:
                await StateManager.safe_update(state, bag_color=color_data)
                color_text = color_names[color_data]

            user_name = callback.from_user.first_name

            # Определяем тип товара для сообщения
            data = await StateManager.get_data_safe(state)
            category_name = data.get('category_name', '')
            is_backpack = self._is_backpack_category(category_name)

            item_type = "рюкзака" if is_backpack else "сумки"
            await callback.message.edit_text(f"{user_name}, цвет {item_type}: {color_text}")

            if is_backpack:
                # Для рюкзаков завершаем выбор свойств и продолжаем процесс
                await self._continue_after_backpack_properties(callback.message, state, user_name)
            else:
                # Для обычных сумок переходим к выбору материала
                await state.set_state(ProductStates.waiting_for_bag_material)
                await self._ask_bag_material(callback.message, user_name)

        except Exception as e:
            print(f"Error in process_bag_color: {e}")
            await callback.answer("❌ Ошибка при выборе цвета")

    async def _continue_after_backpack_properties(self, message: Message, state: FSMContext, user_name: str):
        """Продолжить после выбора свойств рюкзака"""
        data = await StateManager.get_data_safe(state)

        # Формируем сводку по выбранным параметрам рюкзака
        summary_lines = ["✅ Параметры рюкзака установлены:"]

        # Назначение
        bag_gender_names = {"women": "Женщины", "men": "Мужчины", "unisex": "Унисекс"}
        if data.get('bag_gender'):
            summary_lines.append(f"• Для кого: {bag_gender_names.get(data['bag_gender'])}")

        # Цвет
        color_names = {
            "red": "Красный", "white": "Белый", "pink": "Розовый", "burgundy": "Бордовый",
            "blue": "Синий", "yellow": "Жёлтый", "light_blue": "Голубой", "purple": "Фиолетовый",
            "orange": "Оранжевый", "multicolor": "Разноцветный", "gray": "Серый", "beige": "Бежевый",
            "black": "Чёрный", "brown": "Коричневый", "green": "Зелёный", "silver": "Серебряный",
            "gold": "Золотой"
        }
        if data.get('bag_color'):
            summary_lines.append(f"• Цвет: {color_names.get(data['bag_color'])}")

        await message.answer("\n".join(summary_lines))

        # Переходим к следующему шагу - состоянию товара
        await state.set_state(ProductStates.waiting_for_condition)

        from bot.services.product_service import ProductService
        await ProductService.ask_condition(message, user_name)

    async def process_bag_material(self, callback: CallbackQuery, state: FSMContext):
        """Обработка выбора материала сумки"""
        try:
            material_data = callback.data[13:]  # Убираем "bag_material_"

            material_names = {
                "natural_leather": "Натуральная кожа",
                "artificial_leather": "Искусственная кожа",
                "other": "Другой",
                "skip": "Пропустить"
            }

            if material_data not in material_names:
                await callback.answer("❌ Неизвестный материал")
                return

            if material_data == "skip":
                await StateManager.safe_update(state, bag_material="")
                material_text = "не указан"
            else:
                await StateManager.safe_update(state, bag_material=material_data)
                material_text = material_names[material_data]

            user_name = callback.from_user.first_name
            await callback.message.edit_text(f"{user_name}, материал сумки: {material_text}")

            # Завершаем выбор параметров сумки и продолжаем процесс
            await self._continue_after_bag_properties(callback.message, state, user_name)

        except Exception as e:
            print(f"Error in process_bag_material: {e}")
            await callback.answer("❌ Ошибка при выборе материала")

    async def _ask_bag_color(self, message: Message, user_name: str, is_backpack: bool = False):
        """Спросить цвет сумки/рюкзака"""
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

        # Добавляем кнопки цветов (по 3 в ряд)
        for color_name, color_code in colors:
            builder.button(text=color_name, callback_data=f"bag_color_{color_code}")

        # Добавляем кнопку пропуска
        builder.button(text="⏭️ Пропустить", callback_data="bag_color_skip")

        builder.adjust(3, 3, 3, 3, 3, 1)

        item_type = "рюкзак" if is_backpack else "сумку"

        await message.answer(
            f"{user_name}, выберите цвет {item_type}:",
            reply_markup=builder.as_markup()
        )

    async def _ask_bag_material(self, message: Message, user_name: str):
        """Спросить материал сумки"""
        from aiogram.utils.keyboard import InlineKeyboardBuilder

        builder = InlineKeyboardBuilder()

        materials = [
            ("🐮 Натуральная кожа", "natural_leather"),
            ("👞 Искусственная кожа", "artificial_leather"),
            ("📦 Другой материал", "other")
        ]

        for material_name, material_code in materials:
            builder.button(text=material_name, callback_data=f"bag_material_{material_code}")

        # Добавляем кнопку пропуска
        builder.button(text="⏭️ Пропустить", callback_data="bag_material_skip")

        builder.adjust(1)  # Все кнопки в один столбец

        await message.answer(
            f"{user_name}, выберите материал сумки:",
            reply_markup=builder.as_markup()
        )

    async def process_bag_type(self, callback: CallbackQuery, state: FSMContext):
        """Обработка выбора вида сумки"""
        bag_type = callback.data[9:]  # Убираем "bag_type_"

        bag_type_names = {
            "shoulder": "Через плечо",
            "crossbody": "Кросс-боди",
            "sport": "Спортивная",
            "clutch": "Клатч",
            "waist": "Поясная",
            "shopper": "Шопер",
            "beach": "Пляжная",
            "with_handles": "С ручками",
            "accessory": "Аксессуар для сумки"
        }

        await StateManager.safe_update(state, bag_type=bag_type)

        user_name = callback.from_user.first_name
        bag_type_text = bag_type_names.get(bag_type, "не указан")

        await callback.message.edit_text(f"{user_name}, вид сумки: {bag_type_text}")

        # Переходим к выбору назначения
        await self._ask_bag_gender(callback.message, user_name)

    async def process_bag_gender(self, callback: CallbackQuery, state: FSMContext):
        """Обработка выбора назначения сумки/рюкзака"""
        try:
            bag_gender = callback.data[11:]  # Убираем "bag_gender_"

            bag_gender_names = {
                "women": "Женщины",
                "men": "Мужчины",
                "unisex": "Унисекс"
            }

            if bag_gender not in bag_gender_names:
                await callback.answer("❌ Неизвестное назначение")
                return

            await StateManager.safe_update(state, bag_gender=bag_gender)

            user_name = callback.from_user.first_name
            bag_gender_text = bag_gender_names[bag_gender]

            # Определяем тип товара для сообщения
            data = await StateManager.get_data_safe(state)
            category_name = data.get('category_name', '')
            is_backpack = self._is_backpack_category(category_name)

            item_type = "рюкзака" if is_backpack else "сумки"
            await callback.message.edit_text(f"{user_name}, назначение {item_type}: {bag_gender_text}")

            if is_backpack:
                # Для рюкзаков переходим к выбору цвета
                await state.set_state(ProductStates.waiting_for_bag_color)
                await self._ask_bag_color(callback.message, user_name, is_backpack=True)
            else:
                # Для обычных сумок переходим к выбору цвета
                await state.set_state(ProductStates.waiting_for_bag_color)
                await self._ask_bag_color(callback.message, user_name, is_backpack=False)

        except Exception as e:
            print(f"Error in process_bag_gender: {e}")
            await callback.answer("❌ Ошибка при выборе назначения")

    async def _ask_bag_type(self, message: Message, user_name: str):
        """Спросить вид сумки"""
        from aiogram.utils.keyboard import InlineKeyboardBuilder

        builder = InlineKeyboardBuilder()

        bag_types = [
            ("👜 Через плечо", "shoulder"),
            ("🎒 Кросс-боди", "crossbody"),
            ("⚽ Спортивная", "sport"),
            ("👛 Клатч", "clutch"),
            ("💫 Поясная", "waist"),
            ("🛍️ Шопер", "shopper"),
            ("🏖️ Пляжная", "beach"),
            ("👜 С ручками", "with_handles"),
            ("✨ Аксессуар для сумки", "accessory")
        ]

        for type_name, type_code in bag_types:
            builder.button(text=type_name, callback_data=f"bag_type_{type_code}")

        builder.adjust(2)

        await message.answer(
            f"{user_name}, выберите вид сумки:",
            reply_markup=builder.as_markup()
        )

    async def _ask_bag_gender(self, message: Message, user_name: str, is_backpack: bool = False):
        """Спросить назначение сумки/рюкзака"""
        from aiogram.utils.keyboard import InlineKeyboardBuilder

        builder = InlineKeyboardBuilder()

        bag_genders = [
            ("👩 Женщины", "women"),
            ("👨 Мужчины", "men"),
            ("👥 Унисекс", "unisex")
        ]

        for gender_name, gender_code in bag_genders:
            builder.button(text=gender_name, callback_data=f"bag_gender_{gender_code}")

        builder.adjust(2)

        item_type = "рюкзака" if is_backpack else "сумки"

        await message.answer(
            f"{user_name}, для кого предназначен {item_type}:",
            reply_markup=builder.as_markup()
        )

    async def _continue_after_bag_properties(self, message: Message, state: FSMContext, user_name: str):
        """Продолжить после выбора всех свойств сумки"""
        data = await StateManager.get_data_safe(state)

        # Формируем сводку по выбранным параметрам
        summary_lines = ["✅ Параметры сумки установлены:"]

        # Вид сумки
        bag_type_names = {
            "shoulder": "Через плечо", "crossbody": "Кросс-боди", "sport": "Спортивная",
            "clutch": "Клатч", "waist": "Поясная", "shopper": "Шопер",
            "beach": "Пляжная", "with_handles": "С ручками", "accessory": "Аксессуар для сумки"
        }
        if data.get('bag_type'):
            summary_lines.append(f"• Вид: {bag_type_names.get(data['bag_type'])}")

        # Назначение
        bag_gender_names = {"women": "Женщины", "men": "Мужчины", "unisex": "Унисекс"}
        if data.get('bag_gender'):
            summary_lines.append(f"• Для кого: {bag_gender_names.get(data['bag_gender'])}")

        # Цвет
        color_names = {
            "red": "Красный", "white": "Белый", "pink": "Розовый", "burgundy": "Бордовый",
            "blue": "Синий", "yellow": "Жёлтый", "light_blue": "Голубой", "purple": "Фиолетовый",
            "orange": "Оранжевый", "multicolor": "Разноцветный", "gray": "Серый", "beige": "Бежевый",
            "black": "Чёрный", "brown": "Коричневый", "green": "Зелёный", "silver": "Серебряный",
            "gold": "Золотой"
        }
        if data.get('bag_color'):
            summary_lines.append(f"• Цвет: {color_names.get(data['bag_color'])}")

        # Материал
        material_names = {
            "natural_leather": "Натуральная кожа",
            "artificial_leather": "Искусственная кожа",
            "other": "Другой"
        }
        if data.get('bag_material'):
            summary_lines.append(f"• Материал: {material_names.get(data['bag_material'])}")

        await message.answer("\n".join(summary_lines))

        # Переходим к следующему шагу - состоянию товара
        await state.set_state(ProductStates.waiting_for_condition)

        from bot.services.product_service import ProductService
        await ProductService.ask_condition(message, user_name)

    # Обновляем метод _process_brand_success для обработки сумок
    async def _process_brand_success(self, message: Message, state: FSMContext, user_name: str):
        """Продолжение процесса после успешного выбора бренда"""
        data = await StateManager.get_data_safe(state)
        brand = data.get('brand', '')
        category_name = data.get('category_name', '')

        await message.answer(f"✅ Бренд подтвержден: {brand}")

        # Проверяем категорию
        is_bag_category = self._is_bag_category(category_name)
        is_backpack_category = self._is_backpack_category(category_name)

        if is_backpack_category:
            # Для рюкзаков запрашиваем цвет и назначение
            await state.set_state(ProductStates.waiting_for_bag_gender)
            await self._ask_bag_gender(message, user_name, is_backpack=True)
        elif is_bag_category:
            # Для обычных сумок запрашиваем вид
            await state.set_state(ProductStates.waiting_for_bag_type)
            await self._ask_bag_type(message, user_name)
        else:
            # Для других категорий проверяем нужен ли размер
            needs_size = self._needs_size_category(category_name)

            if needs_size:
                await state.set_state(ProductStates.waiting_for_size)
                from bot.services.product_service import ProductService
                await ProductService.ask_size(message, user_name)
            else:
                await state.set_state(ProductStates.waiting_for_condition)
                from bot.services.product_service import ProductService
                await ProductService.ask_condition(message, user_name)

    def _is_bag_category(self, category_name: str) -> bool:
        """Проверяет, является ли категория сумкой"""
        if not category_name:
            return False

        # Разделяем по дефису и берем правую часть
        category_parts = category_name.split('-')
        if len(category_parts) > 1:
            # Берем правую часть после дефиса
            category_for_check = category_parts[-1].strip().lower()
        else:
            # Если дефиса нет, используем всю строку
            category_for_check = category_name.strip().lower()

        bag_keywords = [
            "сумки"
        ]

        return any(keyword in category_for_check for keyword in bag_keywords)

    def _is_backpack_category(self, category_name: str) -> bool:
        """Проверяет, является ли категория рюкзаком"""
        if not category_name:
            return False

        # Разделяем по дефису и берем правую часть
        category_parts = category_name.split('-')
        if len(category_parts) > 1:
            # Берем правую часть после дефиса
            category_for_check = category_parts[-1].strip().lower()
        else:
            # Если дефиса нет, используем всю строку
            category_for_check = category_name.strip().lower()

        backpack_keywords = [
            "рюкзак"
        ]

        return any(keyword in category_for_check for keyword in backpack_keywords)

    def _needs_size_category(self, category_name: str) -> bool:
        """Проверяет, нужен ли размер для категории"""
        if not category_name:
            return False

        size_categories = [
            "Мужская обувь", "Женская обувь", "Мужская одежда", "Женская одежда",
            "Брюки", "Джинсы", "Шорты", "Пиджаки и костюмы", "Рубашки", "Платья", "Юбки",
            "Обувь", "Одежда", "Верхняя одежда", "Нижнее белье", "Головные уборы"
        ]

        return any(size_cat in category_name for size_cat in size_categories)

    async def _ask_backpack_properties(self, message: Message, user_name: str):
        """Запрос свойств для рюкзака"""
        # Начинаем с выбора назначения
        await self._ask_bag_gender(message, user_name, is_backpack=True)

    async def process_backpack_gender(self, callback: CallbackQuery, state: FSMContext):
        """Обработка выбора назначения рюкзака"""
        try:
            bag_gender = callback.data[11:]  # Убираем "bag_gender_"

            bag_gender_names = {
                "women": "Женщины",
                "men": "Мужчины",
                "unisex": "Унисекс"
            }

            if bag_gender not in bag_gender_names:
                await callback.answer("❌ Неизвестное назначение")
                return

            await StateManager.safe_update(state, bag_gender=bag_gender)

            user_name = callback.from_user.first_name
            bag_gender_text = bag_gender_names[bag_gender]

            await callback.message.edit_text(f"{user_name}, назначение рюкзака: {bag_gender_text}")

            # Переходим к выбору цвета
            await state.set_state(ProductStates.waiting_for_bag_color)
            await self._ask_bag_color(callback.message, user_name, is_backpack=True)

        except Exception as e:
            print(f"Error in process_backpack_gender: {e}")
            await callback.answer("❌ Ошибка при выборе назначения")

    async def my_products_command(self, message: Message):
        """Показать все товары пользователя"""
        try:
            user_id = message.from_user.id
            products = await self.db.get_user_products(user_id)

            if not products:
                await message.answer(
                    "📭 У вас пока нет созданных товаров.\n\n"
                    "Используйте /new_product чтобы создать первый товар."
                )
                return

            # Формируем список товаров
            products_text = "📦 Ваши товары:\n\n"
            for i, product in enumerate(products, 1):
                created_at = product.get('created_at', '')
                if created_at and isinstance(created_at, str):
                    created_date = created_at[:10]  # Берем только дату
                else:
                    created_date = 'неизвестно'

                products_text += (
                    f"{i}. **{product.get('title', 'Без названия')[:30]}...**\n"
                    f"   🆔 ID: `{product.get('product_id', 'N/A')}`\n"
                    f"   📁 Категория: {product.get('category_name', 'Не указана')}\n"
                    f"   💰 Цена: {self._format_price(product)}\n"
                    f"   🏙️ Города: {len(product.get('cities', []))}\n"
                    f"   📸 Фото: {len(product.get('all_images', []))}\n"
                    f"   📅 Создан: {created_date}\n"
                    f"   ────────────────────\n"
                )

            await message.answer(products_text, parse_mode="Markdown")

        except Exception as e:
            await message.answer("❌ Ошибка при загрузке списка товаров")

    def _format_price(self, product: dict) -> str:
        """Форматирование цены для отображения"""
        price_type = product.get('price_type', 'none')

        if price_type == 'fixed' and product.get('price'):
            return f"{product['price']} руб."
        elif price_type == 'range' and product.get('price_min') and product.get('price_max'):
            return f"{product['price_min']}-{product['price_max']} руб."
        else:
            return "Не указана"

    async def generate_xml_command(self, message: Message):
        """Генерация XML файла для Avito"""
        try:
            user_id = message.from_user.id
            products = await self.db.get_user_products(user_id)

            if not products:
                await message.answer(
                    "❌ У вас нет товаров для генерации XML.\n\n"
                    "Сначала создайте товары с помощью /new_product"
                )
                return

            # Создаем XML структуру
            xml_content = self._create_avito_xml(products)

            # Сохраняем во временный файл
            filename = f"avito_export_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xml"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(xml_content)

            # Отправляем файл пользователю
            with open(filename, 'rb') as f:
                file_content = f.read()
                await message.answer_document(
                    document=BufferedInputFile(file_content, filename=filename),
                    caption="✅ XML файл для Avito готов!\n\n"
                            "Вы можете загрузить этот файл в личном кабинете Avito."
                )

            # Удаляем временный файл
            os.remove(filename)

        except Exception as e:
            await message.answer("❌ Ошибка при генерации XML файла")

    def _create_avito_xml(self, products: list) -> str:
        """Создание XML структуры для Avito"""
        # Создаем корневой элемент
        root = ET.Element("Ads", formatVersion="3", target="Avito.ru")

        ad_count = 0

        for product in products:
            # Получаем города для размещения
            cities = product.get('cities', [])
            quantity = product.get('quantity', 1)
            placement_method = product.get('placement_method', 'exact_cities')

            # Создаем объявления в зависимости от метода размещения
            if placement_method == 'multiple_in_city' and cities:
                # Мультиразмещение в одном городе
                for i in range(quantity):
                    ad = self._create_ad_element(product, cities[0], i + 1)
                    root.append(ad)
                    ad_count += 1

            elif placement_method == 'by_quantity' and cities:
                # Размещение по количеству в разных городах
                for i in range(min(quantity, len(cities))):
                    city = cities[i] if i < len(cities) else cities[0]
                    ad = self._create_ad_element(product, city, i + 1)
                    root.append(ad)
                    ad_count += 1

            elif placement_method == 'metro' and product.get('selected_metro_stations'):
                # Размещение по станциям метро
                metro_stations = product.get('selected_metro_stations', [])
                metro_city = product.get('metro_city', 'Москва')

                for i, station in enumerate(metro_stations[:quantity]):
                    ad = self._create_ad_element(product, metro_city, i + 1, station)
                    root.append(ad)
                    ad_count += 1

            else:
                # Обычное размещение по городам
                for i, city in enumerate(cities[:quantity]):
                    ad = self._create_ad_element(product, city, i + 1)
                    root.append(ad)
                    ad_count += 1

        # Добавляем информацию о количестве объявлений
        ET.SubElement(root, "TotalAds").text = str(ad_count)

        # Конвертируем в красивый XML
        rough_string = ET.tostring(root, encoding='utf-8')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ")

    def _create_ad_element(self, product: dict, city: str, ad_number: int = 1, metro_station: str = None) -> ET.Element:
        """Создание элемента объявления"""
        ad = ET.Element("Ad")

        # Базовые поля
        product_id = product.get('product_id', 'unknown')
        ET.SubElement(ad, "Id").text = f"{product_id}_{ad_number}" if ad_number > 1 else product_id
        ET.SubElement(ad, "Title").text = product.get('title', 'Без названия')
        ET.SubElement(ad, "Description").text = product.get('description', '')

        # Цена
        price = self._get_product_price(product)
        if price > 0:
            ET.SubElement(ad, "Price").text = str(price)

        # Категория
        category = product.get('category', '')
        if category:
            ET.SubElement(ad, "Category").text = category
            # Добавляем параметры для сумок
        bag_type = product.get('bag_type')
        bag_gender = product.get('bag_gender')
        bag_color = product.get('bag_color')
        bag_material = product.get('bag_material')
        # Вид сумки
        # Определяем тип товара
        category_name = product.get('category_name', '')
        is_backpack = self._is_backpack_category(category_name)

        if is_backpack:
            # Для рюкзаков добавляем только назначение и цвет
            if bag_gender:
                bag_gender_names = {"women": "Женщины", "men": "Мужчины", "unisex": "Унисекс"}
                param = ET.SubElement(ad, "Param")
                ET.SubElement(param, "Name").text = "Для кого"
                ET.SubElement(param, "Value").text = bag_gender_names.get(bag_gender, bag_gender)

            if bag_color:
                color_names = {
                    "red": "Красный", "white": "Белый", "pink": "Розовый", "burgundy": "Бордовый",
                    "blue": "Синий", "yellow": "Жёлтый", "light_blue": "Голубой", "purple": "Фиолетовый",
                    "orange": "Оранжевый", "multicolor": "Разноцветный", "gray": "Серый", "beige": "Бежевый",
                    "black": "Чёрный", "brown": "Коричневый", "green": "Зелёный", "silver": "Серебряный",
                    "gold": "Золотой"
                }
                param = ET.SubElement(ad, "Param")
                ET.SubElement(param, "Name").text = "Цвет"
                ET.SubElement(param, "Value").text = color_names.get(bag_color, bag_color)
        else:
            # Для обычных сумок добавляем все параметры
            if bag_type:
                bag_type_names = {
                    "shoulder": "Через плечо", "crossbody": "Кросс-боди", "sport": "Спортивная",
                    "clutch": "Клатч", "waist": "Поясная", "shopper": "Шопер",
                    "beach": "Пляжная", "with_handles": "С ручками", "accessory": "Аксессуар для сумки"
                }
                param = ET.SubElement(ad, "Param")
                ET.SubElement(param, "Name").text = "Вид одежды, обуви, аксессуаров"
                ET.SubElement(param, "Value").text = bag_type_names.get(bag_type, bag_type)

            if bag_gender:
                bag_gender_names = {"women": "Женщины", "men": "Мужчины", "unisex": "Унисекс"}
                param = ET.SubElement(ad, "Param")
                ET.SubElement(param, "Name").text = "Для кого"
                ET.SubElement(param, "Value").text = bag_gender_names.get(bag_gender, bag_gender)

            if bag_color:
                color_names = {
                    "red": "Красный", "white": "Белый", "pink": "Розовый", "burgundy": "Бордовый",
                    "blue": "Синий", "yellow": "Жёлтый", "light_blue": "Голубой", "purple": "Фиолетовый",
                    "orange": "Оранжевый", "multicolor": "Разноцветный", "gray": "Серый", "beige": "Бежевый",
                    "black": "Чёрный", "brown": "Коричневый", "green": "Зелёный", "silver": "Серебряный",
                    "gold": "Золотой"
                }
                param = ET.SubElement(ad, "Param")
                ET.SubElement(param, "Name").text = "Цвет"
                ET.SubElement(param, "Value").text = color_names.get(bag_color, bag_color)

            if bag_material:
                material_names = {
                    "natural_leather": "Натуральная кожа",
                    "artificial_leather": "Искусственная кожа",
                    "other": "Другой"
                }
                param = ET.SubElement(ad, "Param")
                ET.SubElement(param, "Name").text = "Материал товара"
                ET.SubElement(param, "Value").text = material_names.get(bag_material, bag_material)

        # Адрес
        address = self._generate_address(city, ad_number, metro_station)
        ET.SubElement(ad, "Address").text = address

        # Контактный телефон
        contact_phone = product.get('contact_phone', '')
        if contact_phone:
            ET.SubElement(ad, "ContactPhone").text = contact_phone

        # Состояние товара
        condition = product.get('condition', '')
        if condition:
            condition_names = {
                "new_with_tag": "Новое с биркой",
                "excellent": "Отличное",
                "good": "Хорошее",
                "satisfactory": "Удовлетворительное"
            }
            ET.SubElement(ad, "Condition").text = condition_names.get(condition, condition)

        # Тип объявления
        sale_type = product.get('sale_type', '')
        if sale_type:
            sale_type_names = {
                "manufacturer": "Товар от производителя",
                "resale": "Товар приобретен на продажу",
                "personal": "Частное лицо"
            }
            ET.SubElement(ad, "AdType").text = sale_type_names.get(sale_type, "Товар от производителя")

        # Бренд
        brand = product.get('brand', '')
        if brand and brand != 'Не указан':
            ET.SubElement(ad, "GoodsType").text = brand

        # Размер
        size = product.get('size', '')
        if size:
            param = ET.SubElement(ad, "Param")
            ET.SubElement(param, "Name").text = "Размер"
            ET.SubElement(param, "Value").text = size

        # Способ связи
        contact_method = product.get('contact_method', 'both')
        if contact_method:
            param = ET.SubElement(ad, "Param")
            ET.SubElement(param, "Name").text = "Способ связи"
            if contact_method == 'both':
                ET.SubElement(param, "Value").text = "По телефону и в сообщениях"
            elif contact_method == 'phone':
                ET.SubElement(param, "Value").text = "По телефону"
            elif contact_method == 'message':
                ET.SubElement(param, "Value").text = "В сообщениях"

        # Дата начала (если указана)
        start_date = product.get('start_date')
        if start_date:
            ET.SubElement(ad, "DateBegin").text = start_date.strftime('%Y-%m-%d')

        # Мультиобъявление
        multioffer = product.get('multioffer', False)
        if multioffer:
            ET.SubElement(ad, "MultiOffer").text = "true"

        return ad

    def _generate_address(self, city: str, ad_number: int = 1, metro_station: str = None) -> str:
        """Генерация адреса"""
        streets = [
            "ул. Ленина", "ул. Центральная", "ул. Советская", "ул. Мира",
            "ул. Молодежная", "ул. Школьная", "ул. Садовая", "ул. Лесная",
            "пр. Победы", "пр. Мира", "бульвар Свободы", "пер. Почтовый"
        ]

        street = random.choice(streets)
        building = random.randint(1, 100)

        if metro_station:
            return f"{city}, {street}, д. {building} (м. {metro_station})"
        elif ad_number > 1:
            return f"{city}, {street}, д. {building}, кв. {ad_number}"
        else:
            return f"{city}, {street}, д. {building}"

    def _get_product_price(self, product: dict) -> int:
        """Получение цены товара"""
        price_type = product.get('price_type', 'none')

        if price_type == 'fixed' and product.get('price'):
            return product['price']
        elif price_type == 'range' and product.get('price_min') and product.get('price_max'):
            # Случайная цена из диапазона
            return random.randint(product['price_min'], product['price_max'])
        else:
            return 0


    async def handle_calendar_callback(
        self,
        callback: CallbackQuery,
        callback_data: CalendarCallback,  # Только один параметр callback_data
        state: FSMContext
    ):
        """Обработчик всех callback'ов календаря"""
        current_state = await state.get_state()

        # Проверяем, что мы в правильном состоянии
        if current_state != ProductStates.waiting_for_start_date:
            await callback.answer("Неверное состояние для выбора даты")
            return

        calendar = ProductCalendar()
        selected, date = await calendar.process_selection(callback, callback_data)

        if selected:
            user_name = callback.from_user.first_name

            if date is None:
                # Пользователь выбрал "Пропустить"
                await state.update_data(start_date=None, start_time=None, start_datetime=None)
                await callback.message.answer(f"{user_name}, продажа начнется сразу после публикации.")
                await ProductService.complete_product_creation(callback.message, state, user_name)
            else:
                # Сохраняем дату и переходим к выбору времени
                await state.update_data(start_date=date)
                await state.set_state(ProductStates.waiting_for_start_time)

                builder = InlineKeyboardBuilder()
                popular_times = [
                    "09:00", "10:00", "11:00", "12:00",
                    "13:00", "14:00", "15:00", "16:00",
                    "17:00", "18:00", "19:00", "20:00"
                ]

                for time in popular_times:
                    builder.button(text=time, callback_data=f"time_{time}")

                builder.button(text="✏️ Ввести вручную", callback_data="time_custom")
                builder.adjust(3)

                await callback.message.answer(
                    f"{user_name}, дата начала продажи: {date.strftime('%d.%m.%Y')}\n\n"
                    "⏰ Теперь выберите время начала продажи:",
                    reply_markup=builder.as_markup()
                )

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