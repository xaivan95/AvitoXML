import logging
import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
import config

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class Product:
    def __init__(self):
        self.id = ""
        self.title = ""
        self.description = ""
        self.price = ""
        self.category = ""
        self.condition = ""
        self.ad_type = ""
        self.images = []
        self.address = ""
        self.contact_phone = ""


class AvitoXMLBot:
    def __init__(self):
        self.users_products = {}
        self.current_step = {}

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        user_id = update.effective_user.id

        welcome_text = """
🤖 Добро пожаловать в бот для создания XML файлов для Авито!

С помощью этого бота вы можете:
• Создать объявления для автозагрузки на Авито
• Сформировать валидный XML файл
• Добавить несколько товаров в один файл

Для начала работы используйте команды:
/new_product - добавить новый товар
/my_products - просмотреть добавленные товары
/generate_xml - сгенерировать XML файл
/help - помощь по использованию бота
        """

        await update.message.reply_text(welcome_text)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /help"""
        help_text = """
📖 Помощь по использованию бота:

1. Добавление товаров:
   • Используйте /new_product чтобы начать добавление товара
   • Следуйте инструкциям бота
   • Добавьте все необходимые данные

2. Просмотр товаров:
   • /my_products - посмотреть все добавленные товары
   • Вы можете удалять товары из списка

3. Генерация XML:
   • /generate_xml - создать XML файл
   • Файл будет готов для загрузки на Авито

⚠️ Важно:
• Все поля обязательны для заполнения
• Цена указывается в рублях
• Для изображений используйте прямые ссылки
• Телефон должен быть в формате +7XXXXXXXXXX
        """
        await update.message.reply_text(help_text)

    async def new_product(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начало добавления нового товара"""
        user_id = update.effective_user.id

        if user_id not in self.users_products:
            self.users_products[user_id] = []

        self.current_step[user_id] = 'start'
        self.users_products[user_id].append(Product())

        await update.message.reply_text(
            "🎯 Начинаем добавление нового товара!\n\n"
            "Введите ID товара (уникальный идентификатор):"
        )
        self.current_step[user_id] = 'id'

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка текстовых сообщений"""
        user_id = update.effective_user.id
        text = update.message.text

        if user_id not in self.current_step:
            await update.message.reply_text("Используйте /new_product чтобы начать добавление товара")
            return

        if user_id not in self.users_products or not self.users_products[user_id]:
            await update.message.reply_text("Ошибка: товар не найден. Используйте /new_product чтобы начать заново.")
            del self.current_step[user_id]
            return

        current_product = self.users_products[user_id][-1]

        if self.current_step[user_id] == 'id':
            current_product.id = text
            self.current_step[user_id] = 'title'
            await update.message.reply_text("Введите название товара:")

        elif self.current_step[user_id] == 'title':
            current_product.title = text
            self.current_step[user_id] = 'description'
            await update.message.reply_text("Введите описание товара:")

        elif self.current_step[user_id] == 'description':
            current_product.description = text
            self.current_step[user_id] = 'price'
            await update.message.reply_text("Введите цену товара (в рублях):")

        elif self.current_step[user_id] == 'price':
            if not text.isdigit():
                await update.message.reply_text("Цена должна быть числом. Введите цену еще раз:")
                return
            current_product.price = text
            self.current_step[user_id] = 'category'
            await self.show_categories(update)

        elif self.current_step[user_id] == 'address':
            current_product.address = text
            self.current_step[user_id] = 'phone'
            await update.message.reply_text("Введите контактный телефон в формате +7XXXXXXXXXX:")

        elif self.current_step[user_id] == 'phone':
            if not text.startswith('+7') or len(text) != 12 or not text[1:].isdigit():
                await update.message.reply_text("Неверный формат телефона. Введите в формате +7XXXXXXXXXX:")
                return
            current_product.contact_phone = text
            self.current_step[user_id] = 'images'
            await update.message.reply_text(
                "Введите ссылки на изображения (каждую с новой строки). "
                "Когда закончите, отправьте команду /finish_images"
            )

        elif self.current_step[user_id] == 'images':
            # Обработка ссылок на изображения
            image_links = [link.strip() for link in text.split('\n') if link.strip()]
            current_product.images.extend(image_links)

            await update.message.reply_text(
                f"Добавлено {len(image_links)} ссылок. Всего изображений: {len(current_product.images)}\n"
                "Продолжайте добавлять ссылки или отправьте /finish_images чтобы завершить."
            )

    async def show_categories(self, update: Update):
        """Показать клавиатуру с категориями"""
        categories = list(config.AVITO_CONFIG['categories'].keys())

        # Создаем клавиатуру с категориями (по 2 в ряду)
        keyboard = []
        for i in range(0, len(categories), 2):
            row = categories[i:i + 2]
            keyboard.append([InlineKeyboardButton(cat, callback_data=f"cat_{cat}") for cat in row])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Выберите категорию:", reply_markup=reply_markup)

    async def show_conditions(self, update: Update):
        """Показать клавиатуру с состояниями товара"""
        conditions = list(config.AVITO_CONFIG['conditions'].keys())

        keyboard = [[InlineKeyboardButton(cond, callback_data=f"cond_{cond}")] for cond in conditions]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text("Выберите состояние товара:", reply_markup=reply_markup)

    async def show_ad_types(self, update: Update):
        """Показать клавиатуру с типами объявлений"""
        ad_types = list(config.AVITO_CONFIG['ad_types'].keys())

        keyboard = [[InlineKeyboardButton(ad_type, callback_data=f"type_{ad_type}")] for ad_type in ad_types]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text("Выберите тип объявления:", reply_markup=reply_markup)

    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик нажатий на кнопки"""
        query = update.callback_query
        await query.answer()

        user_id = query.from_user.id
        data = query.data

        if user_id not in self.users_products or not self.users_products[user_id]:
            await query.edit_message_text("Сессия истекла. Используйте /new_product чтобы начать заново.")
            return

        current_product = self.users_products[user_id][-1]

        if data.startswith('cat_'):
            category_name = data[4:]
            current_product.category = str(config.AVITO_CONFIG['categories'][category_name])
            self.current_step[user_id] = 'condition'
            await query.edit_message_text(f"Категория выбрана: {category_name}")
            await self.show_conditions_from_query(query)

        elif data.startswith('cond_'):
            condition_name = data[5:]
            current_product.condition = config.AVITO_CONFIG['conditions'][condition_name]
            self.current_step[user_id] = 'ad_type'
            await query.edit_message_text(f"Состояние выбрано: {condition_name}")
            await self.show_ad_types_from_query(query)

        elif data.startswith('type_'):
            ad_type_name = data[5:]
            current_product.ad_type = config.AVITO_CONFIG['ad_types'][ad_type_name]
            self.current_step[user_id] = 'address'
            await query.edit_message_text(f"Тип объявления выбран: {ad_type_name}")
            await context.bot.send_message(chat_id=user_id, text="Введите адрес:")

    async def show_conditions_from_query(self, query):
        """Показать состояния товара после callback query"""
        conditions = list(config.AVITO_CONFIG['conditions'].keys())
        keyboard = [[InlineKeyboardButton(cond, callback_data=f"cond_{cond}")] for cond in conditions]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text("Выберите состояние товара:", reply_markup=reply_markup)

    async def show_ad_types_from_query(self, query):
        """Показать типы объявлений после callback query"""
        ad_types = list(config.AVITO_CONFIG['ad_types'].keys())
        keyboard = [[InlineKeyboardButton(ad_type, callback_data=f"type_{ad_type}")] for ad_type in ad_types]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text("Выберите тип объявления:", reply_markup=reply_markup)

    async def finish_images(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Завершение добавления изображений"""
        user_id = update.effective_user.id

        if user_id in self.current_step and self.current_step[user_id] == 'images':
            if user_id in self.users_products and self.users_products[user_id]:
                current_product = self.users_products[user_id][-1]

                if not current_product.images:
                    await update.message.reply_text(
                        "Вы не добавили ни одного изображения. Товар добавлен без изображений.")
                else:
                    await update.message.reply_text(f"Добавлено {len(current_product.images)} изображений.")

                # Завершаем добавление товара
                del self.current_step[user_id]

                await update.message.reply_text(
                    f"✅ Товар '{current_product.title}' успешно добавлен!\n\n"
                    f"Используйте /new_product чтобы добавить еще товар\n"
                    f"Используйте /my_products чтобы посмотреть все товары\n"
                    f"Используйте /generate_xml чтобы создать XML файл"
                )
            else:
                await update.message.reply_text(
                    "Ошибка: товар не найден. Используйте /new_product чтобы начать заново.")
                if user_id in self.current_step:
                    del self.current_step[user_id]

    async def my_products(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать все добавленные товары пользователя"""
        user_id = update.effective_user.id

        if user_id not in self.users_products or not self.users_products[user_id]:
            await update.message.reply_text(
                "У вас нет добавленных товаров. Используйте /new_product чтобы добавить товар.")
            return

        products = self.users_products[user_id]
        text = f"📦 Ваши товары ({len(products)}):\n\n"

        for i, product in enumerate(products, 1):
            text += f"{i}. {product.title}\n"
            text += f"   ID: {product.id}\n"
            text += f"   Цена: {product.price} руб.\n"
            text += f"   Изображений: {len(product.images)}\n"
            text += "   ─────────────────────\n"

        text += "\nИспользуйте /delete_product [номер] чтобы удалить товар\nИспользуйте /generate_xml чтобы создать XML файл"

        await update.message.reply_text(text)

    async def delete_product(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Удалить товар по номеру"""
        user_id = update.effective_user.id

        if user_id not in self.users_products or not self.users_products[user_id]:
            await update.message.reply_text("У вас нет товаров для удаления.")
            return

        if not context.args:
            await update.message.reply_text("Укажите номер товара для удаления: /delete_product [номер]")
            return

        try:
            index = int(context.args[0]) - 1
            if 0 <= index < len(self.users_products[user_id]):
                deleted_product = self.users_products[user_id].pop(index)
                await update.message.reply_text(f"Товар '{deleted_product.title}' удален.")

                if not self.users_products[user_id]:
                    await update.message.reply_text(
                        "У вас больше нет товаров. Используйте /new_product чтобы добавить товар.")
            else:
                await update.message.reply_text("Неверный номер товара.")
        except ValueError:
            await update.message.reply_text("Номер должен быть числом.")

    async def generate_xml(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Генерация XML файла"""
        user_id = update.effective_user.id

        if user_id not in self.users_products or not self.users_products[user_id]:
            await update.message.reply_text(
                "У вас нет товаров для генерации XML. Используйте /new_product чтобы добавить товар.")
            return

        try:
            # Создаем корневой элемент
            root = ET.Element("Ads", formatVersion="3", target="Avito.ru")

            for product in self.users_products[user_id]:
                ad = ET.SubElement(root, "Ad")

                # Обязательные поля
                ET.SubElement(ad, "Id").text = product.id
                ET.SubElement(ad, "Title").text = product.title
                ET.SubElement(ad, "Description").text = product.description
                ET.SubElement(ad, "Price").text = product.price
                ET.SubElement(ad, "Category").text = product.category
                ET.SubElement(ad, "Address").text = product.address
                ET.SubElement(ad, "ContactPhone").text = product.contact_phone

                # Необязательные поля
                if product.condition:
                    ET.SubElement(ad, "Condition").text = product.condition
                if product.ad_type:
                    ET.SubElement(ad, "AdType").text = product.ad_type

                # Изображения
                if product.images:
                    images_element = ET.SubElement(ad, "Images")
                    for image_url in product.images[:10]:  # Авито принимает до 10 изображений
                        image_elem = ET.SubElement(images_element, "Image")
                        image_elem.set("url", image_url)

            # Форматируем XML
            rough_string = ET.tostring(root, 'utf-8')
            reparsed = minidom.parseString(rough_string)
            pretty_xml = reparsed.toprettyxml(indent="  ")

            # Сохраняем в файл
            filename = f"avito_export_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xml"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(pretty_xml)

            # Отправляем файл пользователю
            with open(filename, 'rb') as f:
                await update.message.reply_document(
                    document=f,
                    filename=filename,
                    caption="✅ Ваш XML файл для загрузки на Авито готов!\n\n"
                            "Вы можете загрузить этот файл в личном кабинете Авито "
                            "в разделе автозагрузки объявлений."
                )

        except Exception as e:
            logger.error(f"Error generating XML: {e}")
            await update.message.reply_text("Произошла ошибка при генерации XML файла. Попробуйте еще раз.")

    def setup_handlers(self, application):
        """Настройка обработчиков"""
        application.add_handler(CommandHandler("start", self.start))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("new_product", self.new_product))
        application.add_handler(CommandHandler("my_products", self.my_products))
        application.add_handler(CommandHandler("delete_product", self.delete_product))
        application.add_handler(CommandHandler("generate_xml", self.generate_xml))
        application.add_handler(CommandHandler("finish_images", self.finish_images))

        application.add_handler(CallbackQueryHandler(self.button_handler))

        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))


async def main():
    """Запуск бота"""
    if not config.BOT_TOKEN:
        logger.error("BOT_TOKEN not found in environment variables")
        return

    application = Application.builder().token(config.BOT_TOKEN).build()

    bot = AvitoXMLBot()
    bot.setup_handlers(application)

    logger.info("Bot is starting...")

    # Запуск бота
    await application.run_polling()


if __name__ == '__main__':
    import asyncio

    asyncio.run(main())