import calendar
from datetime import datetime
from typing import Tuple, Optional
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters.callback_data import CallbackData


# Callback data для календаря
class CalendarCallback(CallbackData, prefix="calendar"):
    action: str
    year: int
    month: int
    day: int


class ProductCalendar:
    months = ["Янв", "Фев", "Мар", "Апр", "Май", "Июн", "Июл", "Авг", "Сен", "Окт", "Ноя", "Дек"]

    def __init__(self):
        self.now = datetime.now()

    async def start_calendar(self, year: int = None) -> InlineKeyboardMarkup:
        """Начальный экран календаря - выбор года"""
        if year is None:
            year = self.now.year

        inline_kb = InlineKeyboardMarkup(inline_keyboard=[])

        # Строка с годами
        years_row = []
        for value in range(year - 2, year + 3):
            years_row.append(InlineKeyboardButton(
                text=str(value),
                callback_data=CalendarCallback(
                    action="SET_YEAR",
                    year=value,
                    month=-1,
                    day=-1
                ).pack()
            ))
        inline_kb.inline_keyboard.append(years_row)

        # Навигация по годам
        nav_row = [
            InlineKeyboardButton(
                text='<<',
                callback_data=CalendarCallback(
                    action="PREV_YEARS",
                    year=year,
                    month=-1,
                    day=-1
                ).pack()
            ),
            InlineKeyboardButton(
                text='>>',
                callback_data=CalendarCallback(
                    action="NEXT_YEARS",
                    year=year,
                    month=-1,
                    day=-1
                ).pack()
            )
        ]
        inline_kb.inline_keyboard.append(nav_row)

        # Кнопка пропуска
        skip_row = [InlineKeyboardButton(
            text="⏩ Пропустить (начать сразу)",
            callback_data=CalendarCallback(
                action="SKIP",
                year=-1,
                month=-1,
                day=-1
            ).pack()
        )]
        inline_kb.inline_keyboard.append(skip_row)

        return inline_kb

    async def _get_month_kb(self, year: int) -> InlineKeyboardMarkup:
        """Клавиатура выбора месяца"""
        inline_kb = InlineKeyboardMarkup(inline_keyboard=[])

        # Заголовок с годом
        header_row = [
            InlineKeyboardButton(text=" ", callback_data="ignore"),
            InlineKeyboardButton(
                text=str(year),
                callback_data=CalendarCallback(
                    action="START",
                    year=year,
                    month=-1,
                    day=-1
                ).pack()
            ),
            InlineKeyboardButton(text=" ", callback_data="ignore")
        ]
        inline_kb.inline_keyboard.append(header_row)

        # Первые 6 месяцев
        months_row1 = []
        for month in self.months[0:6]:
            months_row1.append(InlineKeyboardButton(
                text=month,
                callback_data=CalendarCallback(
                    action="SET_MONTH",
                    year=year,
                    month=self.months.index(month) + 1,
                    day=-1
                ).pack()
            ))
        inline_kb.inline_keyboard.append(months_row1)

        # Последние 6 месяцев
        months_row2 = []
        for month in self.months[6:12]:
            months_row2.append(InlineKeyboardButton(
                text=month,
                callback_data=CalendarCallback(
                    action="SET_MONTH",
                    year=year,
                    month=self.months.index(month) + 1,
                    day=-1
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
                    month=-1,
                    day=-1
                ).pack()
            ),
            InlineKeyboardButton(
                text="⏩ Пропустить",
                callback_data=CalendarCallback(
                    action="SKIP",
                    year=-1,
                    month=-1,
                    day=-1
                ).pack()
            )
        ]
        inline_kb.inline_keyboard.append(nav_row)

        return inline_kb

    async def _get_days_kb(self, year: int, month: int) -> InlineKeyboardMarkup:
        """Клавиатура выбора дня"""
        inline_kb = InlineKeyboardMarkup(inline_keyboard=[])

        # Заголовок с годом и месяцем
        header_row = [
            InlineKeyboardButton(
                text=str(year),
                callback_data=CalendarCallback(
                    action="START",
                    year=year,
                    month=-1,
                    day=-1
                ).pack()
            ),
            InlineKeyboardButton(
                text=self.months[month - 1],
                callback_data=CalendarCallback(
                    action="SET_YEAR",
                    year=year,
                    month=-1,
                    day=-1
                ).pack()
            )
        ]
        inline_kb.inline_keyboard.append(header_row)

        # Дни недели
        week_days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        week_days_row = []
        for day in week_days:
            week_days_row.append(InlineKeyboardButton(text=day, callback_data="ignore"))
        inline_kb.inline_keyboard.append(week_days_row)

        # Дни месяца
        month_calendar = calendar.monthcalendar(year, month)
        for week in month_calendar:
            week_row = []
            for day in week:
                if day == 0:
                    week_row.append(InlineKeyboardButton(text=" ", callback_data="ignore"))
                else:
                    week_row.append(InlineKeyboardButton(
                        text=str(day),
                        callback_data=CalendarCallback(
                            action="SET_DAY",
                            year=year,
                            month=month,
                            day=day
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
                    day=-1
                ).pack()
            ),
            InlineKeyboardButton(
                text="⏩ Пропустить",
                callback_data=CalendarCallback(
                    action="SKIP",
                    year=-1,
                    month=-1,
                    day=-1
                ).pack()
            )
        ]
        inline_kb.inline_keyboard.append(nav_row)

        return inline_kb

    async def process_selection(self, callback: CallbackQuery, data: CalendarCallback) -> Tuple[
        bool, Optional[datetime]]:
        """Обработка выбора в календаре"""
        return_data = (False, None)

        try:
            if data.action == "IGNORE":
                await callback.answer()
                return return_data

            if data.action == "SKIP":
                await callback.message.delete()
                return True, None

            if data.action == "SET_YEAR":
                await callback.message.edit_reply_markup(
                    reply_markup=await self._get_month_kb(data.year)
                )
                return return_data

            if data.action == "PREV_YEARS":
                new_year = data.year - 5
                await callback.message.edit_reply_markup(
                    reply_markup=await self.start_calendar(new_year)
                )
                return return_data

            if data.action == "NEXT_YEARS":
                new_year = data.year + 5
                await callback.message.edit_reply_markup(
                    reply_markup=await self.start_calendar(new_year)
                )
                return return_data

            if data.action == "START":
                await callback.message.edit_reply_markup(
                    reply_markup=await self.start_calendar(data.year)
                )
                return return_data

            if data.action == "SET_MONTH":
                await callback.message.edit_reply_markup(
                    reply_markup=await self._get_days_kb(data.year, data.month)
                )
                return return_data

            if data.action == "SET_DAY":
                selected_date = datetime(data.year, data.month, data.day)
                await callback.message.delete()
                return True, selected_date

            if data.action == "BACK":
                # Определяем текущий экран по тексту сообщения
                current_text = callback.message.text or ""
                if "месяц" in current_text.lower():
                    await callback.message.edit_reply_markup(
                        reply_markup=await self.start_calendar(data.year)
                    )
                elif "день" in current_text.lower():
                    await callback.message.edit_reply_markup(
                        reply_markup=await self._get_month_kb(data.year)
                    )

        except Exception as e:
            print(f"Calendar processing error: {e}")

        return return_data