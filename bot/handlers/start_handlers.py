# bot/handlers/start_handlers.py
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.database import Database
from bot.handlers.base import BaseHandler
from bot.states import ProductStates
from bot.services.product_service import ProductService


class StartHandlers(BaseHandler):
    """Обработчики стартовых команд"""

    def __init__(self, db: Database, bot: Bot = None):
        router = Router()
        super().__init__(router, db, bot)

    def _register_handlers(self):
        # Команды
        self.router.message.register(self.start_command, CommandStart())
        self.router.message.register(self.help_command, Command("help"))
        self.router.message.register(self.about_command, Command("about"))
        self.router.message.register(self.new_product_command, Command("new_product"))
        self.router.message.register(self.my_products_command, Command("my_products"))

        # Callback обработчики
        self.router.callback_query.register(self.new_product_callback, F.data == "new_product")
        self.router.callback_query.register(self.my_products_callback, F.data == "my_products")
        self.router.callback_query.register(self.help_callback, F.data == "help")
        self.router.callback_query.register(self.back_to_main_callback, F.data == "back_to_main")

        # Новые обработчики для удаления товаров
        self.router.callback_query.register(self.show_delete_product_menu, F.data == "delete_product")
        self.router.callback_query.register(self.select_product_to_delete, F.data.startswith("delete_select_"))
        self.router.callback_query.register(self.confirm_delete_product, F.data.startswith("confirm_delete_"))
        self.router.callback_query.register(self.cancel_delete_product, F.data == "cancel_delete")
        self.router.callback_query.register(self.back_to_products_list, F.data == "back_to_products_list")

    async def start_command(self, message: Message):
        """Обработчик команды /start"""
        user_name = message.from_user.first_name

        builder = InlineKeyboardBuilder()
        builder.button(text="🆕 Создать товар", callback_data="new_product")
        builder.button(text="📋 Мои товары", callback_data="my_products")
        builder.button(text="❓ Помощь", callback_data="help")
        builder.adjust(1)

        welcome_text = (
            f"👋 Привет, {user_name}!\n\n"
            "🤖 Я бот для создания объявлений на Avito.\n\n"
            "📋 <b>Что я умею:</b>\n"
            "• Создавать товары с фотографиями\n"
            "• Указывать цены и характеристики\n"
            "• Настраивать доставку\n"
            "• Генерировать XML для Avito\n\n"
            "🚀 <b>Начните с создания первого товара!</b>"
        )

        await message.answer(welcome_text, reply_markup=builder.as_markup())

    async def new_product_command(self, message: Message, state: FSMContext):
        """Обработчик команды /new_product"""
        await state.clear()

        product_data = {
            'product_id': ProductService.generate_guid(),
            'main_images': [],
            'additional_images': [],
            'shuffle_images': False,
            'avito_delivery': False,
            'delivery_services': []
        }

        await state.update_data(**product_data)
        await state.set_state(ProductStates.waiting_for_category)

        await ProductService.show_main_categories(message, message.from_user.first_name)

    async def new_product_callback(self, callback: CallbackQuery, state: FSMContext):
        """Обработчик кнопки 'Создать товар'"""
        await state.clear()

        product_data = {
            'product_id': ProductService.generate_guid(),
            'main_images': [],
            'additional_images': [],
            'shuffle_images': False,
            'avito_delivery': False,
            'delivery_services': []
        }

        await state.update_data(**product_data)
        await state.set_state(ProductStates.waiting_for_category)

        await callback.message.edit_text("🆕 Запускаем создание нового товара...")
        await ProductService.show_main_categories(callback.message, callback.from_user.first_name)

    async def my_products_command(self, message: Message):
        """Обработчик команды /my_products"""
        from bot.handlers.common_handlers import CommonHandlers
        # Создаем временный экземпляр для вызова метода
        common_handler = CommonHandlers(self.db, self.bot)
        await common_handler.my_products_command(message)

    async def my_products_callback(self, callback: CallbackQuery):
        """Обработчик кнопки 'Мои товары'"""
        try:
            user_id = callback.from_user.id
            products = await self.db.get_user_products(user_id)

            if not products:
                # Нет товаров
                builder = InlineKeyboardBuilder()
                builder.button(text="🆕 Создать первый товар", callback_data="new_product")
                builder.button(text="🔙 Назад", callback_data="back_to_main")
                builder.adjust(1)

                await callback.message.edit_text(
                    "📭 <b>Мои товары</b>\n\n"
                    "У вас пока нет созданных товаров.\n\n"
                    "Создайте первый товар, чтобы начать работу!",
                    reply_markup=builder.as_markup()
                )
                return

            # Формируем список товаров с нумерацией
            products_text = "📦 <b>Ваши товары:</b>\n\n"
            for i, product in enumerate(products, 1):
                created_at = product.get('created_at', '')
                if created_at and isinstance(created_at, str):
                    created_date = created_at[:10]  # Берем только дату
                else:
                    created_date = 'неизвестно'

                products_text += (
                    f"<b>{i}. {product.get('title', 'Без названия')[:30]}...</b>\n"
                    f"   🆔 ID: <code>{product.get('product_id', 'N/A')}</code>\n"
                    f"   📁 Категория: {product.get('category_name', 'Не указана')}\n"
                    f"   💰 Цена: {self._format_price(product)}\n"
                    f"   🏙️ Города: {len(product.get('cities', []))}\n"
                    f"   📸 Фото: {len(product.get('all_images', []))}\n"
                    f"   📅 Создан: {created_date}\n"
                    f"   ────────────────────\n"
                )

            builder = InlineKeyboardBuilder()
            builder.button(text="🗑️ Удалить товар", callback_data="delete_product")
            #builder.button(text="📦 Сгенерировать XML", callback_data="generate_xml")
            builder.button(text="🆕 Новый товар", callback_data="new_product")
            builder.button(text="🔙 Назад", callback_data="back_to_main")
            builder.adjust(1)

            await callback.message.edit_text(
                products_text + "\n💡 Выберите действие:",
                reply_markup=builder.as_markup(),
                parse_mode="HTML"
            )

        except Exception as e:
            print(f"Error in my_products_callback: {e}")
            await callback.message.edit_text(
                "❌ Ошибка при загрузке списка товаров\n\n"
                "Попробуйте позже или обратитесь к администратору."
            )

    async def show_delete_product_menu(self, callback: CallbackQuery):
        """Показать меню выбора товара для удаления"""
        try:
            user_id = callback.from_user.id
            products = await self.db.get_user_products(user_id)

            if not products:
                await callback.answer("❌ У вас нет товаров для удаления")
                return

            builder = InlineKeyboardBuilder()

            # Добавляем кнопки для каждого товара
            for i, product in enumerate(products, 1):
                product_title = product.get('title', 'Без названия')[:25]
                product_id = product.get('product_id')
                builder.button(
                    text=f"{i}. {product_title}...",
                    callback_data=f"delete_select_{product_id}"
                )

            # Кнопки навигации
            builder.button(text="🔙 Назад к списку", callback_data="back_to_products_list")
            builder.button(text="🏠 В главное меню", callback_data="back_to_main")
            builder.adjust(1)

            await callback.message.edit_text(
                "🗑️ <b>Удаление товара</b>\n\n"
                "Выберите товар для удаления:\n\n"
                "⚠️ <i>Внимание: удаление нельзя отменить!</i>",
                reply_markup=builder.as_markup(),
                parse_mode="HTML"
            )

        except Exception as e:
            print(f"Error in show_delete_product_menu: {e}")
            await callback.answer("❌ Ошибка при загрузке списка товаров")

    async def select_product_to_delete(self, callback: CallbackQuery):
        """Обработка выбора товара для удаления"""
        try:
            product_id = callback.data[14:]  # Убираем "delete_select_"

            # Получаем информацию о товаре
            product = await self.db.get_product_by_id(product_id)

            if not product:
                await callback.answer("❌ Товар не найден")
                return

            builder = InlineKeyboardBuilder()
            builder.button(
                text="✅ Да, удалить",
                callback_data=f"confirm_delete_{product_id}"
            )
            builder.button(
                text="❌ Отмена",
                callback_data="cancel_delete"
            )
            builder.adjust(2)

            product_title = product.get('title', 'Без названия')
            product_category = product.get('category_name', 'Не указана')
            product_price = self._format_price(product)

            await callback.message.edit_text(
                f"🗑️ <b>Подтверждение удаления</b>\n\n"
                f"<b>Товар:</b> {product_title}\n"
                f"<b>Категория:</b> {product_category}\n"
                f"<b>Цена:</b> {product_price}\n"
                f"<b>Фото:</b> {len(product.get('all_images', []))} шт.\n\n"
                f"⚠️ <b>Вы уверены, что хотите удалить этот товар?</b>\n"
                f"<i>Это действие нельзя отменить!</i>",
                reply_markup=builder.as_markup(),
                parse_mode="HTML"
            )

        except Exception as e:
            print(f"Error in select_product_to_delete: {e}")
            await callback.answer("❌ Ошибка при выборе товара")

    async def confirm_delete_product(self, callback: CallbackQuery):
        """Подтверждение и удаление товара"""
        try:
            product_id = callback.data[15:]  # Убираем "confirm_delete_"
            user_id = callback.from_user.id

            # Находим индекс товара для удаления
            products = await self.db.get_user_products(user_id)
            product_index = None

            for i, product in enumerate(products):
                if product.get('product_id') == product_id:
                    product_index = i
                    break

            if product_index is None:
                await callback.answer("❌ Товар не найден")
                return

            # Удаляем товар
            success = await self.db.delete_product(user_id, product_index)

            if success:
                # Показываем обновленный список товаров
                products = await self.db.get_user_products(user_id)

                if not products:
                    # Если товаров не осталось
                    builder = InlineKeyboardBuilder()
                    builder.button(text="🆕 Создать товар", callback_data="new_product")
                    builder.button(text="🏠 В главное меню", callback_data="back_to_main")
                    builder.adjust(1)

                    await callback.message.edit_text(
                        "✅ <b>Товар успешно удален!</b>\n\n"
                        "📭 У вас больше нет товаров.\n\n"
                        "Создайте новый товар, чтобы продолжить работу!",
                        reply_markup=builder.as_markup(),
                        parse_mode="HTML"
                    )
                else:
                    # Показываем обновленный список
                    builder = InlineKeyboardBuilder()
                    builder.button(text="🗑️ Удалить еще товар", callback_data="delete_product")
                    #builder.button(text="📦 Сгенерировать XML", callback_data="/generate_xml")
                    builder.button(text="🆕 Новый товар", callback_data="new_product")
                    builder.button(text="🏠 В главное меню", callback_data="back_to_main")
                    builder.adjust(1)

                    products_text = "✅ <b>Товар успешно удален!</b>\n\n📦 <b>Ваши товары:</b>\n\n"
                    for i, product in enumerate(products, 1):
                        created_at = product.get('created_at', '')
                        if created_at and isinstance(created_at, str):
                            created_date = created_at[:10]
                        else:
                            created_date = 'неизвестно'

                        products_text += (
                            f"<b>{i}. {product.get('title', 'Без названия')[:30]}...</b>\n"
                            f"   📁 {product.get('category_name', 'Не указана')}\n"
                            f"   💰 {self._format_price(product)}\n"
                            f"   ────────────────────\n"
                        )

                    await callback.message.edit_text(
                        products_text,
                        reply_markup=builder.as_markup(),
                        parse_mode="HTML"
                    )
            else:
                await callback.message.edit_text(
                    "❌ <b>Ошибка при удалении товара</b>\n\n"
                    "Попробуйте еще раз или обратитесь к администратору.",
                    parse_mode="HTML"
                )

        except Exception as e:
            print(f"Error in confirm_delete_product: {e}")
            await callback.message.edit_text(
                "❌ <b>Ошибка при удалении товара</b>\n\n"
                "Попробуйте еще раз или обратитесь к администратору.",
                parse_mode="HTML"
            )

    async def cancel_delete_product(self, callback: CallbackQuery):
        """Отмена удаления товара"""
        await callback.message.edit_text(
            "❌ <b>Удаление отменено</b>\n\n"
            "Товар не был удален.",
            parse_mode="HTML"
        )
        # Возвращаемся к списку товаров
        await self.my_products_callback(callback)

    async def back_to_products_list(self, callback: CallbackQuery):
        """Возврат к списку товаров"""
        await self.my_products_callback(callback)

    def _format_price(self, product: dict) -> str:
        """Форматирование цены для отображения"""
        price_type = product.get('price_type', 'none')

        if price_type == 'fixed' and product.get('price'):
            return f"{product['price']} руб."
        elif price_type == 'range' and product.get('price_min') and product.get('price_max'):
            return f"{product['price_min']}-{product['price_max']} руб."
        else:
            return "Не указана"

    async def help_callback(self, callback: CallbackQuery):
        """Обработчик кнопки 'Помощь'"""
        help_text = (
            "📖 <b>Справка по командам:</b>\n\n"
            "🆕 <b>Создать товар</b> - начать процесс создания нового товара\n"
            "📋 <b>Мои товары</b> - просмотр созданных товаров\n"
            "📦 <b>Генерация XML</b> - создание файла для Avito\n\n"
            "💡 <b>Процесс создания товара:</b>\n"
            "1. Выберите категорию\n"
            "2. Добавьте фото\n"
            "3. Укажите параметры\n"
            "4. Настройте размещение\n"
            "5. Получите XML файл\n\n"
            "❓ <b>Проблемы?</b> Обратитесь к администратору."
        )

        builder = InlineKeyboardBuilder()
        builder.button(text="🔙 Назад в меню", callback_data="back_to_main")
        builder.adjust(1)

        await callback.message.edit_text(help_text, reply_markup=builder.as_markup())

    async def back_to_main_callback(self, callback: CallbackQuery, state: FSMContext):
        """Обработчик кнопки 'Назад в меню'"""
        await state.clear()  # Очищаем состояние

        user_name = callback.from_user.first_name

        builder = InlineKeyboardBuilder()
        builder.button(text="🆕 Создать товар", callback_data="new_product")
        builder.button(text="📋 Мои товары", callback_data="my_products")
        builder.button(text="❓ Помощь", callback_data="help")
        builder.adjust(1)

        welcome_text = (
            f"👋 С возвращением, {user_name}!\n\n"
            "🤖 Я бот для создания объявлений на Avito.\n\n"
            "📋 <b>Что я умею:</b>\n"
            "• Создавать товары с фотографиями\n"
            "• Указывать цены и характеристики\n"
            "• Настраивать доставку\n"
            "• Генерировать XML для Avito\n\n"
            "🚀 <b>Выберите действие:</b>"
        )

        await callback.message.edit_text(welcome_text, reply_markup=builder.as_markup())

    async def help_command(self, message: Message):
        """Обработчик команды /help"""
        help_text = (
            "📖 <b>Справка по командам:</b>\n\n"
            "🆕 <b>/new_product</b> - создать новый товар\n"
            "📋 <b>/my_products</b> - посмотреть мои товары\n"
            "📦 <b>/generate_xml</b> - сгенерировать XML для Avito\n"
            "🆘 <b>/help</b> - показать эту справку\n"
            "ℹ️ <b>/about</b> - информация о боте\n\n"
            "💡 <b>Процесс создания товара:</b>\n"
            "1. Выберите категорию\n"
            "2. Добавьте фото\n"
            "3. Укажите параметры\n"
            "4. Настройте размещение\n"
            "5. Получите XML файл\n\n"
            "❓ <b>Проблемы?</b> Обратитесь к администратору."
        )

        await message.answer(help_text)

    async def about_command(self, message: Message):
        """Обработчик команды /about"""
        about_text = (
            "🤖 <b>Avito Product Bot</b>\n\n"
            "📊 <b>Версия:</b> 2.0\n"
            "🔧 <b>Разработчик:</b> Ваша команда\n"
            "📅 <b>Обновлено:</b> 2024\n\n"
            "⚡ <b>Возможности:</b>\n"
            "• Создание товаров для Avito\n"
            "• Управление фотографиями\n"
            "• Настройка доставки\n"
            "• Генерация XML выгрузок\n\n"
            "💎 <b>Преимущества:</b>\n"
            "• Простой интерфейс\n"
            "• Быстрое создание объявлений\n"
            "• Поддержка всех параметров Avito\n"
            "• Надежное хранение данных\n\n"
            "📞 <b>Поддержка:</b> @your_support"
        )

        await message.answer(about_text)