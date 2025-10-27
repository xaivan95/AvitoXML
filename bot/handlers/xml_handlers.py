import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
import tempfile
import os
from bot.database import db

router = Router()


@router.message(Command("my_products"))
async def my_products_command(message: Message):
    user_id = message.from_user.id
    products = await db.get_user_products(user_id)

    if not products:
        await message.answer("У вас нет добавленных товаров. Используйте /new_product чтобы добавить товар.")
        return

    text = f"📦 Ваши товары ({len(products)}):\n\n"

    for i, product in enumerate(products, 1):
        text += f"{i}. {product.title}\n"
        text += f"   ID: {product.product_id}\n"
        text += f"   Цена: {product.price} руб.\n"
        text += f"   Изображений: {len(product.images)}\n"
        text += "   ─────────────────────\n"

    text += "\nИспользуйте /delete_product [номер] чтобы удалить товар\nИспользуйте /generate_xml чтобы создать XML файл"

    await message.answer(text)


@router.message(Command("delete_product"))
async def delete_product_command(message: Message):
    user_id = message.from_user.id
    args = message.text.split()[1:] if len(message.text.split()) > 1 else []

    if not args:
        await message.answer("Укажите номер товара для удаления: /delete_product [номер]")
        return

    try:
        index = int(args[0]) - 1
        success = await db.delete_product(user_id, index)
        if success:
            await message.answer("Товар успешно удален.")
        else:
            await message.answer("Неверный номер товара.")
    except ValueError:
        await message.answer("Номер должен быть числом.")


@router.message(Command("generate_xml"))
async def generate_xml_command(message: Message):
    user_id = message.from_user.id
    products = await db.get_user_products(user_id)

    if not products:
        await message.answer("У вас нет товаров для генерации XML. Используйте /new_product чтобы добавить товар.")
        return

    try:
        # Создаем корневой элемент
        root = ET.Element("Ads", formatVersion="3", target="Avito.ru")

        for product in products:
            ad = ET.SubElement(root, "Ad")

            # Обязательные поля
            ET.SubElement(ad, "Id").text = product.product_id
            ET.SubElement(ad, "Title").text = product.title
            ET.SubElement(ad, "Description").text = product.description
            ET.SubElement(ad, "Price").text = str(product.price)
            ET.SubElement(ad, "Category").text = product.category
            ET.SubElement(ad, "Address").text = product.address
            ET.SubElement(ad, "ContactPhone").text = product.contact_phone

            # Необязательные поля
            if product.condition:
                ET.SubElement(ad, "Condition").text = product.condition
            if product.ad_type:
                ET.SubElement(ad, "AdType").text = product.ad_type

            # Изображения
            if product.images:
                images_element = ET.SubElement(ad, "Images")
                for image_url in product.images[:10]:  # Авито принимает до 10 изображений
                    image_elem = ET.SubElement(images_element, "Image")
                    image_elem.set("url", image_url)

        # Форматируем XML
        rough_string = ET.tostring(root, 'utf-8')
        reparsed = minidom.parseString(rough_string)
        pretty_xml = reparsed.toprettyxml(indent="  ")

        # Создаем временный файл
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False, encoding='utf-8') as f:
            f.write(pretty_xml)
            temp_filename = f.name

        # Отправляем файл пользователю
        with open(temp_filename, 'rb') as f:
            await message.answer_document(
                document=f,
                caption="✅ Ваш XML файл для загрузки на Авито готов!\n\n"
                        "Вы можете загрузить этот файл в личном кабинете Авито "
                        "в разделе автозагрузки объявлений."
            )

        # Удаляем временный файл
        os.unlink(temp_filename)

    except Exception as e:
        print(f"Error generating XML: {e}")
        await message.answer("Произошла ошибка при генерации XML файла. Попробуйте еще раз.")