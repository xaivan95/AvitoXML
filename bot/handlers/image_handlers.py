# bot/handlers/image_handlers.py
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from typing import Dict, List
from datetime import datetime

from bot.states import ProductStates
from bot.handlers.base import BaseHandler, StateManager


async def _ask_shuffle_images(message: Message, state: FSMContext, user_name: str = ""):
    """Запрос о перемешивании фото"""
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Да, перемешать", callback_data="shuffle_yes")
    builder.button(text="❌ Нет, оставить как есть", callback_data="shuffle_no")
    builder.adjust(1)

    greeting = f"{user_name}, " if user_name else ""

    data = await StateManager.get_data_safe(state)
    main_count = len(data.get('main_images', []))
    additional_count = len(data.get('additional_images', []))
    total_count = main_count + additional_count

    await message.answer(
        f"{greeting}нужно ли перемешать фото?\n\n"
        f"📊 Статистика фото:\n"
        f"• Основные: {main_count}\n"
        f"• Дополнительные: {additional_count}\n"
        f"• Всего: {total_count}\n\n"
        "При перемешивании все фото будут расположены в случайном порядке.",
        reply_markup=builder.as_markup()
    )


class ImageHandlers(BaseHandler):
    """Обработчики для работы с изображениями"""

    def __init__(self, bot: Bot = None):
        router = Router()
        # ImageHandlers может не требовать db
        super().__init__(router, None, bot)

    def _register_handlers(self):
        # Основные изображения
        self.router.message.register(
            self.handle_main_images_album,
            StateFilter(ProductStates.waiting_for_main_images),
            F.media_group_id
        )
        self.router.message.register(
            self.process_main_single_image,
            StateFilter(ProductStates.waiting_for_main_images),
            F.photo
        )

        # Дополнительные изображения
        self.router.message.register(
            self.handle_additional_images_album,
            StateFilter(ProductStates.waiting_for_additional_images),
            F.media_group_id
        )
        self.router.message.register(
            self.process_additional_single_image,
            StateFilter(ProductStates.waiting_for_additional_images),
            F.photo
        )

        # Команды завершения
        self.router.message.register(
            self.finish_main_images_command,
            Command("finish_main_images")
        )
        self.router.message.register(
            self.finish_additional_images_command,
            Command("finish_additional_images")
        )

        # Перемешивание изображений
        self.router.callback_query.register(
            self.process_shuffle_choice,
            F.data.startswith("shuffle_")
        )

    async def handle_main_images_album(self, message: Message, album: List[Message], state: FSMContext):
        """Обработка альбома основных изображений"""
        if not album:
            return

        photo_files = []
        for msg in album:
            if msg.photo:
                largest_photo = msg.photo[-1]
                photo_files.append(largest_photo.file_id)

        if photo_files:
            data = await StateManager.get_data_safe(state)
            main_images = data.get('main_images', [])
            main_images.extend(photo_files)

            await StateManager.safe_update(state, main_images=main_images)

            await message.answer(
                f"✅ Добавлен альбом с {len(photo_files)} основными фото! "
                f"Всего основных фото: {len(main_images)}\n\n"
                "Продолжайте отправлять фото или нажмите /finish_main_images чтобы завершить."
            )

    async def process_main_single_image(self, message: Message, state: FSMContext):
        """Обработка одиночного основного изображения"""
        if message.media_group_id:
            return  # Обрабатывается в handle_main_images_album

        largest_photo = message.photo[-1]
        photo_file_id = largest_photo.file_id

        data = await StateManager.get_data_safe(state)
        main_images = data.get('main_images', [])
        main_images.append(photo_file_id)

        await StateManager.safe_update(state, main_images=main_images)

        await message.answer(
            f"✅ Получено 1 основное изображение! Всего основных фото: {len(main_images)}\n\n"
            "Продолжайте отправлять фото или нажмите /finish_main_images чтобы завершить."
        )

    async def handle_additional_images_album(self, message: Message, album: List[Message], state: FSMContext):
        """Обработка альбома дополнительных изображений"""
        if not album:
            return

        photo_files = []
        for msg in album:
            if msg.photo:
                largest_photo = msg.photo[-1]
                photo_files.append(largest_photo.file_id)

        if photo_files:
            data = await StateManager.get_data_safe(state)
            additional_images = data.get('additional_images', [])
            additional_images.extend(photo_files)

            await StateManager.safe_update(state, additional_images=additional_images)

            total_count = len(additional_images)
            await message.answer(
                f"✅ Добавлен альбом с {len(photo_files)} дополнительными фото! "
                f"Всего дополнительных фото: {total_count}\n\n"
                "Продолжайте отправлять фото или нажмите /finish_additional_images чтобы завершить."
            )

    async def process_additional_single_image(self, message: Message, state: FSMContext):
        """Обработка одиночного дополнительного изображения"""
        if message.media_group_id:
            return  # Обрабатывается в handle_additional_images_album

        data = await StateManager.get_data_safe(state)
        additional_images = data.get('additional_images', [])

        largest_photo = message.photo[-1]
        additional_images.append(largest_photo.file_id)

        await StateManager.safe_update(state, additional_images=additional_images)

        await message.answer(
            f"✅ Дополнительное изображение добавлено! "
            f"Всего дополнительных фото: {len(additional_images)}\n\n"
            "Продолжайте отправлять фото или нажмите /finish_additional_images чтобы завершить."
        )

    async def finish_main_images_command(self, message: Message, state: FSMContext):
        """Завершение добавления основных изображений"""
        data = await StateManager.get_data_safe(state)
        main_images = data.get('main_images', [])

        await state.set_state(ProductStates.waiting_for_additional_images)

        user_name = message.from_user.first_name
        if main_images:
            await message.answer(
                f"{user_name}, ✅ завершено добавление основных изображений! "
                f"Всего: {len(main_images)}\n\n"
                "Теперь переходим к дополнительным фотографиям."
            )
        else:
            await message.answer(
                f"{user_name}, основных изображений нет. "
                "Переходим к дополнительным фотографиям."
            )

        await self._ask_additional_images(message, state, user_name)

    async def finish_additional_images_command(self, message: Message, state: FSMContext):
        """Завершение добавления дополнительных изображений"""
        data = await StateManager.get_data_safe(state)
        additional_images = data.get('additional_images', [])

        await state.set_state(ProductStates.waiting_for_shuffle_images)

        user_name = message.from_user.first_name

        # Показываем итоговую статистику
        main_images = data.get('main_images', [])
        total_main = len(main_images)
        total_additional = len(additional_images)
        total_all = total_main + total_additional

        await message.answer(
            f"{user_name}, завершено добавление дополнительных фото!\n\n"
            f"📊 Статистика фото:\n"
            f"• Основные: {total_main}\n"
            f"• Дополнительные: {total_additional}\n"
            f"• Всего: {total_all}\n\n"
            "Теперь нужно решить, перемешивать ли фото."
        )

        await _ask_shuffle_images(message, state, user_name)

    async def process_shuffle_choice(self, callback: CallbackQuery, state: FSMContext):
        """Обработка выбора перемешивания фото"""
        shuffle_choice = callback.data[8:]  # Убираем "shuffle_"

        shuffle_images = (shuffle_choice == "yes")
        await StateManager.safe_update(state, shuffle_images=shuffle_images)
        await state.set_state(ProductStates.waiting_for_avito_delivery)

        user_name = callback.from_user.first_name
        choice_text = "перемешаны" if shuffle_images else "оставлены в исходном порядке"

        await callback.message.edit_text(
            f"{user_name}, фото будут {choice_text}.\n\n"
            "Теперь уточним настройки доставки."
        )

        from bot.services.delivery_service import DeliveryService
        await DeliveryService.ask_avito_delivery(callback.message, user_name)

    async def _ask_additional_images(self, message: Message, state: FSMContext, user_name: str = ""):
        """Запрос дополнительных изображений"""
        greeting = f"{user_name}, " if user_name else ""

        data = await StateManager.get_data_safe(state)
        main_count = len(data.get('main_images', []))

        await message.answer(
            f"{greeting}теперь отправьте ДОПОЛНИТЕЛЬНЫЕ фотографии объявления.\n\n"
            f"📸 У вас уже {main_count} основных фото\n"
            "Вы можете отправлять:\n"
            "• 📷 По одному фото\n"
            "• 🖼️ Несколько фото одним сообщением (альбом)\n"
            "• 📤 Несколько сообщениями\n\n"
            "После отправки всех дополнительных фото нажмите /finish_additional_images\n\n"
            "💡 Если дополнительных фото нет, просто нажмите /finish_additional_images"
        )

