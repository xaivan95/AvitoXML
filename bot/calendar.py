# bot/calendar.py
from datetime import datetime, timedelta, date
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters.callback_data import CallbackData
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import Optional


class CalendarCallback(CallbackData, prefix="calendar"):
    action: str
    year: Optional[int] = None
    month: Optional[int] = None
    day: Optional[int] = None


class ProductCalendar:
    def __init__(self):
        self.today = datetime.now().date()

    async def start_calendar(self) -> InlineKeyboardMarkup:
        """Начало календаря с быстрыми кнопками"""
        builder = InlineKeyboardBuilder()

        # Быстрые кнопки
        quick_dates = [
            ("📅 Завтра", "tomorrow"),
            ("📅 Через 3 дня", "3_days"),
            ("📅 Через неделю", "7_days"),
            ("📅 Через 2 недели", "14_days")
        ]

        for text, action in quick_dates:
            builder.button(text=text, callback_data=CalendarCallback(action=action))

        builder.button(text="📅 Выбрать дату вручную", callback_data=CalendarCallback(action="manual"))
        builder.button(text="⏩ Пропустить", callback_data=CalendarCallback(action="skip"))

        builder.adjust(2, 2, 1, 1)

        return builder.as_markup()

    async def process_selection(self, callback_query, callback_data: CalendarCallback) -> tuple:
        """Обработка выбора даты"""
        return_data = (False, None)

        if callback_data.action == "skip":
            return True, None

        elif callback_data.action == "manual":
            # Переход к ручному выбору даты
            await self._show_month_selection(callback_query)
            return False, None

        elif callback_data.action == "back_to_quick":
            # Возврат к быстрому выбору
            await callback_query.message.edit_reply_markup(
                reply_markup=await self.start_calendar()
            )
            return False, None

        elif callback_data.action in ["tomorrow", "3_days", "7_days", "14_days"]:
            # Обработка быстрых кнопок
            selected_date = self._get_quick_date(callback_data.action)
            return True, selected_date

        elif callback_data.action == "day":
            # Выбор конкретного дня
            return_data = await self._process_day_selection(callback_data)

        elif callback_data.action == "prev-month":
            # Навигация по месяцам
            await self._show_month_selection(callback_query, year=callback_data.year, month=callback_data.month)

        elif callback_data.action == "next-month":
            # Навигация по месяцам
            await self._show_month_selection(callback_query, year=callback_data.year, month=callback_data.month)

        elif callback_data.action == "ignore":
            # Игнорируем
            await callback_query.answer(cache_time=60)

        return return_data

    def _get_quick_date(self, action: str) -> date:
        """Получить дату для быстрой кнопки"""
        today = self.today

        if action == "tomorrow":
            return today + timedelta(days=1)
        elif action == "3_days":
            return today + timedelta(days=3)
        elif action == "7_days":
            return today + timedelta(days=7)
        elif action == "14_days":
            return today + timedelta(days=14)

        return today

    async def _show_month_selection(self, callback_query, year: int = None, month: int = None):
        """Показать выбор месяца с ограничениями"""
        now = datetime.now()
        if year is None:
            year = now.year
        if month is None:
            month = now.month

        # Создаем клавиатуру для выбора месяца
        builder = InlineKeyboardBuilder()

        # Определяем, можно ли переходить к предыдущему месяцу
        can_go_prev = not (year == now.year and month == now.month)

        # Кнопки навигации
        prev_month = month - 1 if month > 1 else 12
        prev_year = year if month > 1 else year - 1
        next_month = month + 1 if month < 12 else 1
        next_year = year if month < 12 else year + 1

        # Кнопка предыдущего месяца (только если не текущий месяц)
        if can_go_prev:
            builder.button(
                text="◀️",
                callback_data=CalendarCallback(action="prev-month", year=prev_year, month=prev_month)
            )
        else:
            builder.button(text="❌", callback_data=CalendarCallback(action="ignore"))

        builder.button(
            text=f"{self._get_month_name(month)} {year}",
            callback_data=CalendarCallback(action="ignore")
        )

        # Кнопка следующего месяца (всегда активна)
        builder.button(
            text="▶️",
            callback_data=CalendarCallback(action="next-month", year=next_year, month=next_month)
        )

        # Дни месяца (только будущие даты активны)
        days = self._get_month_days(year, month)
        today = self.today

        for day in days:
            current_date = date(year, month, day)
            if current_date >= today:
                # Будущая дата - активная кнопка
                builder.button(
                    text=f"{day}",
                    callback_data=CalendarCallback(action="day", year=year, month=month, day=day)
                )
            else:
                # Прошедшая дата - неактивная кнопка
                builder.button(
                    text=f"❌",
                    callback_data=CalendarCallback(action="ignore")
                )

        # Кнопка возврата
        builder.button(
            text="🔙 Назад к быстрому выбору",
            callback_data=CalendarCallback(action="back_to_quick")
        )

        # Рассчитываем layout: 3 кнопки навигации, затем дни по 7 в ряд, затем 1 кнопка возврата
        builder.adjust(3, *[7 for _ in range((len(days) + 6) // 7)], 1)

        await callback_query.message.edit_reply_markup(reply_markup=builder.as_markup())

    def _get_month_name(self, month: int) -> str:
        """Получить название месяца"""
        months = [
            "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
            "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
        ]
        return months[month - 1]

    def _get_month_days(self, year: int, month: int) -> list:
        """Получить список дней месяца"""
        import calendar
        cal = calendar.monthcalendar(year, month)
        days = []
        for week in cal:
            for day in week:
                if day != 0:
                    days.append(day)
        return days

    async def _process_day_selection(self, callback_data: CalendarCallback) -> tuple:
        """Обработка выбора дня"""
        selected_date = date(
            year=callback_data.year,
            month=callback_data.month,
            day=callback_data.day
        )

        # Проверяем, что выбранная дата не в прошлом
        if selected_date < self.today:
            return False, None

        return True, selected_date