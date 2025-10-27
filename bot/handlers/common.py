from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

router = Router()

@router.message(Command("start"))
async def start_command(message: Message):
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
    await message.answer(welcome_text)

@router.message(Command("help"))
async def help_command(message: Message):
    help_text = """
📖 Помощь по использованию бота:

1. Добавление товаров:
   • Используйте /new_product чтобы начать добавление товара
   • Следуйте инструкции бота
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
    await message.answer(help_text)

@router.message(Command("cancel"))
async def cancel_command(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Действие отменено.")