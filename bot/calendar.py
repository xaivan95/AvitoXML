import calendar
from datetime import datetime, timedelta
from typing import Tuple, Optional
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters.callback_data import CallbackData


class CalendarCallback(CallbackData, prefix="calendar"):
    action: str
    year: int
    month: int
    day: int


class ProductCalendar:
    months = ["Янв", "Фев", "Мар", "Апр", "Май", "Июн", "Июл", "Авг", "Сен", "Окт", "Ноя", "Дек"]

    def __init__(self):
        self.now = datetime.now()
        self.today = datetime.now().date()

    async def start_calendar(self) -> InlineKeyboardMarkup:
        """Начальный экран календаря - выбор года (начинаем с текущего)"""
        current_year = self.now.year

        inline_kb = InlineKeyboardMarkup(inline_keyboard=[])

        # Строка с годами (начинаем с текущего)
        years_row = []
        for value in range(current_year, current_year + 5):
            years_row.append(InlineKeyboardButton(
                text=str(value),
                callback_data=CalendarCallback(
                    action="SET_YEAR",
                    year=value,
                    month=0,
                    day=0
                ).pack()
            ))
        inline_kb.inline_keyboard.append(years_row)

        # Навигация по годам
        nav_row = [
            InlineKeyboardButton(
                text='<<',
                callback_data=CalendarCallback(
                    action="PREV_YEARS",
                    year=current_year,
                    month=0,
                    day=0
                ).pack()
            ),
            InlineKeyboardButton(
                text='>>',
                callback_data=CalendarCallback(
                    action="NEXT_YEARS",
                    year=current_year,
                    month=0,
                    day=0
                ).pack()
            )
        ]
        inline_kb.inline_keyboard.append(nav_row)

        # Кнопка пропуска
        skip_button = InlineKeyboardButton(
            text="⏩ Пропустить (начать сразу)",
            callback_data=CalendarCallback(
                action="SKIP",
                year=0,
                month=0,
                day=0
            ).pack()
        )
        inline_kb.inline_keyboard.append([skip_button])

        return inline_kb

    async def _get_month_kb(self, year: int) -> InlineKeyboardMarkup:
        """Клавиатура выбора месяца с проверкой на будущие года"""
        inline_kb = InlineKeyboardMarkup(inline_keyboard=[])

        # Заголовок с годом
        header_row = [
            InlineKeyboardButton(
                text=str(year),
                callback_data=CalendarCallback(
                    action="START",
                    year=year,
                    month=0,
                    day=0
                ).pack()
            )
        ]
        inline_kb.inline_keyboard.append(header_row)

        # Определяем доступные месяцы
        current_year = self.now.year
        current_month = self.now.month

        # Первые 6 месяцев
        months_row1 = []
        for i, month in enumerate(self.months[0:6], 1):
            # Проверяем, не в прошлом ли месяц
            if year > current_year or (year == current_year and i >= current_month):
                months_row1.append(InlineKeyboardButton(
                    text=month,
                    callback_data=CalendarCallback(
                        action="SET_MONTH",
                        year=year,
                        month=i,
                        day=0
                    ).pack()
                ))
            else:
                months_row1.append(InlineKeyboardButton(
                    text="❌",
                    callback_data=CalendarCallback(
                        action="IGNORE",
                        year=0,
                        month=0,
                        day=0
                    ).pack()
                ))
        inline_kb.inline_keyboard.append(months_row1)

        # Последние 6 месяцев
        months_row2 = []
        for i, month in enumerate(self.months[6:12], 7):
            # Проверяем, не в прошлом ли месяц
            if year > current_year or (year == current_year and i >= current_month):
                months_row2.append(InlineKeyboardButton(
                    text=month,
                    callback_data=CalendarCallback(
                        action="SET_MONTH",
                        year=year,
                        month=i,
                        day=0
                    ).pack()
                ))
            else:
                months_row2.append(InlineKeyboardButton(
                    text="❌",
                    callback_data=CalendarCallback(
                        action="IGNORE",
                        year=0,
                        month=0,
                        day=0
                    ).pack()
                ))
        inline_kb.inline_keyboard.append(months_row2)

        # Кнопки навигации
        nav_row = [
            InlineKeyboardButton(
                text='🔙 Назад',
                callback_data=CalendarCallback(
                    action="BACK",
                    year=year,
                    month=0,
                    day=0
                ).pack()
            )
        ]
        inline_kb.inline_keyboard.append(nav_row)

        return inline_kb

    async def _get_days_kb(self, year: int, month: int) -> InlineKeyboardMarkup:
        """Клавиатура выбора дня с проверкой на прошлые даты"""
        inline_kb = InlineKeyboardMarkup(inline_keyboard=[])

        # Заголовок с годом и месяцем
        header_row = [
            InlineKeyboardButton(
                text=f"{self.months[month - 1]} {year}",
                callback_data=CalendarCallback(
                    action="SET_YEAR",
                    year=year,
                    month=0,
                    day=0
                ).pack()
            )
        ]
        inline_kb.inline_keyboard.append(header_row)

        # Дни недели
        week_days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        week_days_row = []
        for day in week_days:
            week_days_row.append(InlineKeyboardButton(
                text=day,
                callback_data=CalendarCallback(
                    action="IGNORE",
                    year=0,
                    month=0,
                    day=0
                ).pack()
            ))
        inline_kb.inline_keyboard.append(week_days_row)

        # Дни месяца с проверкой на доступность
        month_calendar = calendar.monthcalendar(year, month)
        today = self.today

        for week in month_calendar:
            week_row = []
            for day in week:
                if day == 0:
                    week_row.append(InlineKeyboardButton(
                        text=" ",
                        callback_data=CalendarCallback(
                            action="IGNORE",
                            year=0,
                            month=0,
                            day=0
                        ).pack()
                    ))
                else:
                    current_date = datetime(year, month, day).date()
                    if current_date >= today:
                        # Доступная дата
                        week_row.append(InlineKeyboardButton(
                            text=str(day),
                            callback_data=CalendarCallback(
                                action="SET_DAY",
                                year=year,
                                month=month,
                                day=day
                            ).pack()
                        ))
                    else:
                        # Прошедшая дата
                        week_row.append(InlineKeyboardButton(
                            text="❌",
                            callback_data=CalendarCallback(
                                action="IGNORE",
                                year=0,
                                month=0,
                                day=0
                            ).pack()
                        ))
            inline_kb.inline_keyboard.append(week_row)

        # Кнопки навигации
        nav_row = [
            InlineKeyboardButton(
                text='🔙 Назад',
                callback_data=CalendarCallback(
                    action="BACK",
                    year=year,
                    month=month,
                    day=0
                ).pack()
            )
        ]
        inline_kb.inline_keyboard.append(nav_row)

        return inline_kb

    async def process_selection(self, callback: CallbackQuery, data: CalendarCallback) -> Tuple[
        bool, Optional[datetime]]:
        """Обработка выбора в календаре"""
        try:
            if data.action == "IGNORE":
                await callback.answer("Эта дата недоступна", show_alert=True)
                return False, None

            if data.action == "SKIP":
                await callback.message.delete()
                return True, None

            if data.action == "SET_YEAR":
                markup = await self._get_month_kb(data.year)
                await callback.message.edit_reply_markup(reply_markup=markup)
                return False, None

            if data.action == "PREV_YEARS":
                new_year = max(self.now.year, data.year - 5)  # Не уходим в прошлое
                markup = await self.start_calendar()
                await callback.message.edit_reply_markup(reply_markup=markup)
                return False, None

            if data.action == "NEXT_YEARS":
                new_year = data.year + 5
                markup = await self.start_calendar()
                await callback.message.edit_reply_markup(reply_markup=markup)
                return False, None

            if data.action == "START":
                markup = await self.start_calendar()
                await callback.message.edit_reply_markup(reply_markup=markup)
                return False, None

            if data.action == "SET_MONTH":
                markup = await self._get_days_kb(data.year, data.month)
                await callback.message.edit_reply_markup(reply_markup=markup)
                return False, None

            if data.action == "SET_DAY":
                selected_date = datetime(data.year, data.month, data.day)
                await callback.message.delete()
                return True, selected_date

            if data.action == "BACK":
                # Всегда возвращаем к начальному экрану
                markup = await self.start_calendar()
                await callback.message.edit_reply_markup(reply_markup=markup)
                return False, None

        except Exception as e:
            print(f"Calendar processing error: {e}")
            await callback.answer("Произошла ошибка", show_alert=True)

        return False, None