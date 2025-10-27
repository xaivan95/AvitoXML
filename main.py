import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from bot.database import db
from bot.middleware import UserStateMiddleware, CallbackUserStateMiddleware, AlbumMiddleware

# Импорт роутеров
from bot.handlers.common import router as common_router
from bot.handlers.product_handlers import router as product_router
from bot.handlers.xml_handlers import router as xml_router

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    # Инициализация бота и диспетчера
    bot = Bot(token=BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Регистрация middleware
    dp.message.middleware(UserStateMiddleware())
    dp.message.middleware(AlbumMiddleware())  # Добавляем AlbumMiddleware
    dp.callback_query.middleware(CallbackUserStateMiddleware())

    # Регистрация роутеров
    dp.include_router(common_router)
    dp.include_router(product_router)
    dp.include_router(xml_router)

    # Загрузка данных при запуске
    await db.load_data()
    logger.info("Данные загружены")

    # Запуск бота
    logger.info("Бот запущен")
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())