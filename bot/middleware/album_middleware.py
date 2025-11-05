# bot/middlewares/album_middleware.py
from aiogram import BaseMiddleware
from aiogram.types import Message
from typing import Dict, Any, Callable, Awaitable
import asyncio


class AlbumMiddleware(BaseMiddleware):
    def __init__(self, latency: float = 1.0):
        self.latency = latency
        self.albums: Dict[str, Dict[str, Any]] = {}

    async def __call__(
            self,
            handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
            event: Message,
            data: Dict[str, Any]
    ) -> Any:

        # Если сообщение не содержит фото, передаем как есть
        if not event.photo:
            return await handler(event, data)

        # Если нет media_group_id, это одиночное фото
        if not event.media_group_id:
            return await handler(event, data)

        media_group_id = event.media_group_id

        # Если это новый альбом
        if media_group_id not in self.albums:
            self.albums[media_group_id] = {
                'messages': [event],
                'handler_called': False
            }

            # Создаем задачу для обработки альбома через latency секунд
            asyncio.create_task(
                self._process_album(media_group_id, handler, data)
            )
        else:
            # Добавляем сообщение в существующий альбом
            self.albums[media_group_id]['messages'].append(event)

        # Никогда не вызываем хендлер сразу для отдельных сообщений альбома
        return None

    async def _process_album(self, media_group_id: str, handler: Callable, data: Dict[str, Any]):
        """Обработка альбома после задержки"""
        try:
            # Ждем указанное время для сбора всех сообщений альбома
            await asyncio.sleep(self.latency)

            if media_group_id not in self.albums:
                return

            album_data = self.albums[media_group_id]
            messages = album_data['messages']

            if not messages or album_data['handler_called']:
                return

            # Помечаем как обработанный
            album_data['handler_called'] = True

            # Берем первое сообщение альбома для обработки
            first_message = messages[0]

            # Передаем альбом через data, а не через атрибут сообщения
            data['album'] = messages

            # Передаем в хендлер
            await handler(first_message, data)

        except Exception as e:
            print(f"Error processing album: {e}")
        finally:
            # Удаляем альбом из кэша
            if media_group_id in self.albums:
                del self.albums[media_group_id]