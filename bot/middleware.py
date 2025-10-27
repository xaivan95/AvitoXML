from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from bot.database import db

class UserStateMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        user_id = event.from_user.id
        user_state = await db.get_user_state(user_id)
        data['user_state'] = user_state
        return await handler(event, data)

class CallbackUserStateMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[CallbackQuery, Dict[str, Any]], Awaitable[Any]],
        event: CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        user_id = event.from_user.id
        user_state = await db.get_user_state(user_id)
        data['user_state'] = user_state
        return await handler(event, data)

class AlbumMiddleware(BaseMiddleware):
    """Middleware для обработки альбомов (нескольких фото в одном сообщении)"""
    def __init__(self):
        super().__init__()

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        if not event.media_group_id:
            return await handler(event, data)

        # Если это медиагруппа, сохраняем информацию о ней
        data['media_group_id'] = event.media_group_id
        data['is_album'] = True
        return await handler(event, data)