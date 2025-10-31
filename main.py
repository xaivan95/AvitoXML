# main.py
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot.handlers import get_all_routers
import config

# Настройка логирования
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

    # Инициализация бота с настройками по умолчанию
    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    # Инициализация диспетчера с хранилищем в памяти
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Регистрация middleware (если нужно)
    await setup_middleware(dp)

    # Регистрация всех роутеров
    await register_routers(dp)

    # Регистрация обработчиков ошибок
    await register_error_handlers(dp)

    # Запуск бота
    await start_bot(bot, dp)


async def setup_middleware(dp: Dispatcher):
    """Настройка middleware"""
    # Здесь можно добавить кастомные middleware
    # Например, для логирования, ограничений и т.д.
    logger.info("Middleware setup completed")


async def register_routers(dp: Dispatcher):
    """Регистрация всех роутеров"""
    try:
        routers = get_all_routers()

        for router in routers:
            dp.include_router(router)
            logger.info(f"Router {router.__class__.__name__} registered")

        logger.info(f"Total routers registered: {len(routers)}")

    except Exception as e:
        logger.error(f"Error registering routers: {e}")
        raise


async def register_error_handlers(dp: Dispatcher):
    """Регистрация обработчиков ошибок"""

    @dp.error()
    async def global_error_handler(event, exception: Exception):
        """Глобальный обработчик ошибок"""
        logger.error(f"Global error handler: {exception}", exc_info=True)

        # Можно отправить сообщение администратору
        # или пользователю в зависимости от типа ошибки

        return True  # Подавляем дальнейшую обработку ошибки


async def start_bot(bot: Bot, dp: Dispatcher):
    """Запуск бота с обработкой graceful shutdown"""
    try:
        logger.info("Starting bot...")

        # Удаляем вебхук (на всякий случай)
        await bot.delete_webhook(drop_pending_updates=True)

        # Запускаем поллинг
        await dp.start_polling(bot)

    except Exception as e:
        logger.error(f"Error starting bot: {e}")

    finally:
        logger.info("Bot stopped")
        await bot.session.close()


async def on_startup(bot: Bot):
    """Действия при запуске бота"""
    logger.info("Bot starting up...")

    # Отправляем сообщение администратору
    try:
        if hasattr(config, 'ADMIN_IDS'):
            for admin_id in config.ADMIN_IDS:
                await bot.send_message(
                    admin_id,
                    "🤖 Бот запущен и готов к работе!"
                )
    except Exception as e:
        logger.error(f"Error sending startup message: {e}")


async def on_shutdown(bot: Bot):
    """Действия при остановке бота"""
    logger.info("Bot shutting down...")

    # Отправляем сообщение администратору
    try:
        if hasattr(config, 'ADMIN_IDS'):
            for admin_id in config.ADMIN_IDS:
                await bot.send_message(
                    admin_id,
                    "🔴 Бот остановлен!"
                )
    except Exception as e:
        logger.error(f"Error sending shutdown message: {e}")

    # Закрываем сессию
    await bot.session.close()


def setup_dispatcher_events(dp: Dispatcher, bot: Bot):
    """Настройка событий диспетчера"""
    dp.startup.register(lambda: on_startup(bot))
    dp.shutdown.register(lambda: on_shutdown(bot))


if __name__ == "__main__":
    try:
        # Проверка конфигурации
        if not hasattr(config, 'BOT_TOKEN') or not config.BOT_TOKEN:
            raise ValueError("BOT_TOKEN not found in config")

        logger.info("Configuration check passed")

        # Запуск основного приложения
        asyncio.run(main())

    except KeyboardInterrupt:
        logger.info("Bot stopped by user")

    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise