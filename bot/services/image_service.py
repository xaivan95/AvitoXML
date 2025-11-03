# bot/services/image_service.py
import os
import requests
from aiogram import Bot
from typing import List, Optional
import tempfile
import uuid


class ImageService:
    """Сервис для работы с изображениями"""

    def __init__(self, bot: Bot):
        self.bot = bot

    async def download_telegram_image(self, file_id: str) -> Optional[bytes]:
        """Скачивает изображение из Telegram по file_id"""
        try:
            # Получаем информацию о файле
            file = await self.bot.get_file(file_id)

            # Скачиваем файл
            file_content = await self.bot.download_file(file.file_path)
            return file_content

        except Exception as e:
            print(f"Error downloading Telegram image {file_id}: {e}")
            return None

    def is_telegram_file_id(self, file_reference: str) -> bool:
        """Проверяет, является ли строка file_id Telegram"""
        if not file_reference:
            return False

        # Telegram file_id обычно начинается с определенных префиксов
        telegram_prefixes = [
            'AgAC', 'BAAC', 'CAAC', 'DAAC', 'AQAD', 'BQAD', 'CQAD', 'DQAD'
        ]

        return any(file_reference.startswith(prefix) for prefix in telegram_prefixes)

    def is_url(self, file_reference: str) -> bool:
        """Проверяет, является ли строка URL"""
        if not file_reference:
            return False

        return file_reference.startswith(('http://', 'https://'))

    async def process_image_for_export(self, image_ref: str) -> Optional[bytes]:
        """Обрабатывает изображение для экспорта (скачивает из Telegram или по URL)"""
        try:
            if self.is_telegram_file_id(image_ref):
                # Скачиваем из Telegram
                return await self.download_telegram_image(image_ref)

            elif self.is_url(image_ref):
                # Скачиваем по URL
                response = requests.get(image_ref, timeout=30)
                if response.status_code == 200:
                    return response.content
                else:
                    print(f"Error downloading URL image: {response.status_code}")
                    return None

            else:
                print(f"Unknown image reference type: {image_ref}")
                return None

        except Exception as e:
            print(f"Error processing image {image_ref}: {e}")
            return None