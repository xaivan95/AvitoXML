# bot/keyboards/builders.py
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardMarkup, KeyboardButton
from typing import List, Tuple, Optional


class KeyboardBuilder:
    """Построитель клавиатур"""

    @staticmethod
    def create_inline_keyboard(
            buttons: List[Tuple[str, str]],
            adjust: int = 1,
            back_button: bool = False,
            back_callback: str = "back"
    ) -> InlineKeyboardBuilder:
        """Создание инлайн клавиатуры"""
        builder = InlineKeyboardBuilder()

        for text, callback_data in buttons:
            builder.button(text=text, callback_data=callback_data)

        if back_button:
            builder.button(text="🔙 Назад", callback_data=back_callback)

        builder.adjust(adjust)
        return builder

    @staticmethod
    def create_simple_reply_keyboard(buttons: List[List[str]]) -> ReplyKeyboardMarkup:
        """Создание reply клавиатуры"""
        keyboard_buttons = []
        for row in buttons:
            keyboard_row = [KeyboardButton(text=text) for text in row]
            keyboard_buttons.append(keyboard_row)

        return ReplyKeyboardMarkup(
            keyboard=keyboard_buttons,
            resize_keyboard=True,
            one_time_keyboard=True
        )

    @staticmethod
    def create_phone_keyboard() -> ReplyKeyboardMarkup:
        """Клавиатура для номера телефона"""
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="📞 Поделиться номером", request_contact=True)],
                [KeyboardButton(text="✏️ Ввести вручную")]
            ],
            resize_keyboard=True,
            one_time_keyboard=True
        )


class ProductKeyboards:
    """Клавиатуры для создания товара"""

    @staticmethod
    def get_price_type_keyboard() -> InlineKeyboardBuilder:
        """Клавиатура выбора типа цены"""
        buttons = [
            ("💰 Фиксированная цена", "price_fixed"),
            ("📊 Диапазон цен", "price_range"),
            ("⏩ Пропустить", "price_skip")
        ]
        return KeyboardBuilder.create_inline_keyboard(buttons, adjust=1)

    @staticmethod
    def get_contact_methods_keyboard() -> InlineKeyboardBuilder:
        """Клавиатура выбора способа связи"""
        buttons = [
            ("📞 По телефону и в сообщении 💬", "contact_both"),
            ("📞 По телефону", "contact_phone"),
            ("💬 В сообщении", "contact_message")
        ]
        return KeyboardBuilder.create_inline_keyboard(buttons, adjust=1)

    @staticmethod
    def get_placement_type_keyboard() -> InlineKeyboardBuilder:
        """Клавиатура выбора типа размещения"""
        buttons = [
            ("🏙️ По городам", "cities"),
            ("🚇 По станциям метро", "metro")
        ]
        return KeyboardBuilder.create_inline_keyboard(buttons, adjust=1)

    @staticmethod
    def get_condition_keyboard() -> InlineKeyboardBuilder:
        """Клавиатура выбора состояния товара"""
        buttons = [
            ("🆕 Новое с биркой", "condition_new_with_tag"),
            ("⭐ Отличное", "condition_excellent"),
            ("👍 Хорошее", "condition_good"),
            ("✅ Удовлетворительное", "condition_satisfactory")
        ]
        return KeyboardBuilder.create_inline_keyboard(buttons, adjust=1)