# bot/services/image_service.py
from typing import Optional

from aiogram import Bot


class ImageService:
    """Сервис для работы с изображениями"""

    def __init__(self, bot: Bot):
        self.bot = bot

    async def process_image_for_export(self, image_ref: str) -> Optional[bytes]:
        """Обрабатывает изображение для экспорта"""
        try:
            if self.is_telegram_file_id(image_ref):
                return await self.download_telegram_image(image_ref)
            elif self.is_url(image_ref):
                return await self.download_url_image_async(image_ref)
            return None
        except Exception as e:
            print(f"Error processing image {image_ref}: {e}")
            return None

    async def download_url_image_async(self, image_url: str) -> Optional[bytes]:
        """Скачивает изображение по URL (асинхронно)"""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url, timeout=30) as response:
                    if response.status == 200:
                        return await response.read()
                    else:
                        print(f"Error downloading URL image {image_url}: status {response.status}")
                        return None
        except Exception as e:
            print(f"Error downloading URL image {image_url}: {e}")
            return None

    async def download_telegram_image(self, file_id: str) -> Optional[bytes]:
        """Скачивает изображение из Telegram по file_id"""
        try:
            file = await self.bot.get_file(file_id)
            file_io = await self.bot.download_file(file.file_path)

            if file_io:
                file_io.seek(0)
                image_bytes = file_io.read()
                file_io.close()
                return image_bytes
            return None

        except Exception as e:
            print(f"Error downloading Telegram image {file_id}: {e}")
            return None

    def is_telegram_file_id(self, file_reference: str) -> bool:
        telegram_prefixes = ['AgAC', 'BAAC', 'CAAC', 'DAAC', 'AQAD', 'BQAD', 'CQAD', 'DQAD']
        return any(file_reference.startswith(prefix) for prefix in telegram_prefixes) if file_reference else False

    def is_url(self, file_reference: str) -> bool:
        return file_reference.startswith(('http://', 'https://')) if file_reference else False