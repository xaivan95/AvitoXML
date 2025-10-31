# bot/services/brand_service.py
from typing import List
import xml.etree.ElementTree as ET
import re

from aiogram.types import Message


class BrandService:
    """Сервис для работы с брендами"""

    @staticmethod
    def load_brands() -> List[str]:
        """Загрузка брендов из XML"""
        try:
            return BrandService._load_brands_standard()
        except Exception:
            return BrandService._load_brands_fallback()

    @staticmethod
    def _load_brands_standard() -> List[str]:
        """Стандартный парсинг XML"""
        try:
            tree = ET.parse('brands.xml')
            root = tree.getroot()

            brands = []
            if root.tag == 'Brendy_fashion':
                for brand_elem in root.findall('brand'):
                    brand_name = brand_elem.get('name')
                    if brand_name:
                        brands.append(brand_name)
            else:
                for brand_elem in root.findall('.//brand'):
                    brand_name = brand_elem.get('name')
                    if brand_name:
                        brands.append(brand_name)
                    elif brand_elem.text:
                        brands.append(brand_elem.text.strip())

            return brands

        except ET.ParseError:
            raise Exception("XML parse error")

    @staticmethod
    def _load_brands_fallback() -> List[str]:
        """Альтернативный способ загрузки"""
        try:
            with open('brands.xml', 'r', encoding='utf-8') as f:
                content = f.read()

            brands = []
            patterns = [
                r'name="([^"]*)"',
                r'<brand[^>]*>([^<]+)</brand>',
                r'<brand\s+[^>]*name\s*=\s*["\']([^"\']*)["\']'
            ]

            for pattern in patterns:
                matches = re.findall(pattern, content)
                brands.extend(matches)

            return list(set([brand for brand in brands if brand.strip()]))

        except Exception:
            return BrandService._get_default_brands()

    @staticmethod
    def _get_default_brands() -> List[str]:
        """Бренды по умолчанию"""
        return [
            "Nike", "Adidas", "Reebok", "Puma", "No name", "Другой бренд",
            "Zara", "H&M", "Uniqlo"
        ]

    @staticmethod
    def is_valid_brand(brand: str) -> bool:
        """Проверка валидности бренда"""
        brands = BrandService.load_brands()
        brand_lower = brand.lower().strip()
        return any(existing_brand.lower().strip() == brand_lower for existing_brand in brands)

    @staticmethod
    def search_brands(query: str, limit: int = 10) -> List[str]:
        """Поиск брендов"""
        brands = BrandService.load_brands()
        query_lower = query.lower().strip()

        matches = [brand for brand in brands if query_lower in brand.lower()]
        return matches[:limit]

    @staticmethod
    async def ask_brand_manual(message: Message, user_name: str = ""):
        """Запрос бренда с ручным вводом и подсказками"""
        greeting = f"{user_name}, " if user_name else ""

        sample_brands = BrandService.load_brands()[:5]
        sample_text = "\n".join([f"• {brand}" for brand in sample_brands])

        await message.answer(
            f"{greeting}введите название бренда:\n\n"
            f"📋 Примеры брендов из базы:\n{sample_text}\n\n"
            "💡 Бренд будет проверен в базе данных.\n"
            "🔍 Можно ввести часть названия для поиска."
        )