from abc import ABC, abstractmethod
from typing import Optional

from aiogram import Router, Bot
from aiogram.fsm.context import FSMContext

from bot.database import Database


class BaseHandler(ABC):
    """Базовый класс для всех обработчиков"""

    def __init__(self, router: Router, db: Database, bot: Optional[Bot] = None):
        self.router = router
        self.db = db
        self.bot = bot
        self._register_handlers()


    @abstractmethod
    def _register_handlers(self):
        """Регистрация обработчиков"""
        pass


class StateManager:
    """Менеджер для работы с состоянием"""

    @staticmethod
    async def safe_update(state: FSMContext, **kwargs):
        """Безопасное обновление состояния"""
        try:
            await state.update_data(**kwargs)
        except Exception as e:
            print(f"State update error: {e}")

    @staticmethod
    async def get_data_safe(state: FSMContext, key: str = None):
        """Безопасное получение данных из состояния"""
        try:
            data = await state.get_data()
            return data.get(key) if key else data
        except Exception as e:
            print(f"State get data error: {e}")
            return None