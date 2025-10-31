# main.py
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot.database import db  # ✅ Импортируем глобальный экземпляр
import config
from bot.handlers import initialize_handlers

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("bot.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


async def main():
    """Основная функция запуска бота"""
    try:
        await db.create_pool()
        logger.info("File database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return

    # Инициализация бота
    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    routers = initialize_handlers(db)
    for router in routers:
        dp.include_router(router)

    logger.info(f"Total routers registered: {len(routers)}")

    # Запуск бота
    await start_bot(bot, dp)


async def register_routers(dp: Dispatcher):
    """Регистрация всех роутеров"""
    try:
        routers = initialize_handlers(db)
        for router in routers:
            dp.include_router(router)
        logger.info(f"Total routers registered: {len(routers)}")
    except Exception as e:
        logger.error(f"Error registering routers: {e}")
        raise


async def start_bot(bot: Bot, dp: Dispatcher):
    """Запуск бота"""
    try:
        logger.info("Starting bot...")
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
    finally:
        logger.info("Bot stopped")
        # Сохраняем данные при завершении
        await db.close()
        await bot.session.close()


if __name__ == "__main__":
    try:
        if not hasattr(config, 'BOT_TOKEN') or not config.BOT_TOKEN:
            raise ValueError("BOT_TOKEN not found in config")
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise