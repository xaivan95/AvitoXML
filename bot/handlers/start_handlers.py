# bot/handlers/start_handlers.py (дополнение)
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.database import Database
from bot.handlers.base import BaseHandler


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

        self.router.callback_query.register(self.help_callback, F.data == "help")

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

    async def new_product_callback(self, callback: CallbackQuery):
        """Обработчик кнопки 'Создать товар'"""
        from aiogram.fsm.context import FSMContext
        from bot.states import ProductStates
        from bot.services.product_service import ProductService

        # Получаем FSM context (нужно передать извне или использовать middleware)
        # В реальном коде это делается через dependency injection
        await callback.message.edit_text("🆕 Запускаем создание нового товара...")

        # Имитируем команду /new_product
        await ProductService.show_main_categories(callback.message, callback.from_user.first_name)
        await callback.answer()

    async def my_products_callback(self, callback: CallbackQuery):
        """Обработчик кнопки 'Мои товары'"""
        # Здесь будет логика показа товаров пользователя
        await callback.message.edit_text(
            "📋 <b>Мои товары</b>\n\n"
            "Здесь будут отображаться все созданные вами товары.\n\n"
            "⚡ Функция в разработке..."
        )
        await callback.answer()

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

        await callback.message.edit_text(help_text)
        await callback.answer()

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



