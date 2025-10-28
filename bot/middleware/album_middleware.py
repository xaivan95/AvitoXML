import asyncio
from typing import Any, Dict, Callable, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message


class AlbumMiddleware(BaseMiddleware):
    """Middleware for handling media groups"""

    def __init__(self, latency: float = 0.5):
        self.latency = latency
        self.albums: Dict[str, Dict[str, Any]] = {}

    async def __call__(
            self,
            handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
            event: Message,
            data: Dict[str, Any]
    ) -> Any:

        # Если это не медиа-группа, передаем как есть
        if not event.media_group_id:
            data['album'] = [event]
            return await handler(event, data)

        # Обработка медиа-группы
        media_group_id = event.media_group_id

        if media_group_id not in self.albums:
            self.albums[media_group_id] = {
                'messages': [],
                'is_processing': False
            }

        album_data = self.albums[media_group_id]
        album_data['messages'].append(event)

        # Если альбом уже обрабатывается, пропускаем
        if album_data['is_processing']:
            return

        # Помечаем как обрабатываемый
        album_data['is_processing'] = True

        # Ждем другие сообщения из группы
        await asyncio.sleep(self.latency)

        # Передаем все сообщения группы в хендлер
        data['album'] = album_data['messages']
        result = await handler(event, data)

        # Удаляем обработанную группу
        if media_group_id in self.albums:
            del self.albums[media_group_id]

        return result