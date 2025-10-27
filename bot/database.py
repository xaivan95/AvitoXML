import json
import aiofiles
import os
import uuid
from datetime import datetime
from typing import Dict, List, Optional


class UserState:
    def __init__(self, user_id: int, state: str = '', data: dict = None):
        self.user_id = user_id
        self.state = state
        self.data = data or {}
        self.created_at = datetime.now()
        self.updated_at = datetime.now()


class Product:
    def __init__(self, user_id: int, product_data: dict):
        self.user_id = user_id

        # Генерируем GUID если не передан
        self.product_id = product_data.get('product_id', str(uuid.uuid4()))
        self.title = product_data.get('title')
        self.description = product_data.get('description')
        self.price = product_data.get('price')
        self.price_type = product_data.get('price_type', 'none')
        self.price_min = product_data.get('price_min')
        self.price_max = product_data.get('price_max')
        self.category = product_data.get('category')
        self.category_name = product_data.get('category_name', '')
        self.contact_phone = product_data.get('contact_phone')
        self.display_phone = product_data.get('display_phone', '')
        self.contact_method = product_data.get('contact_method', 'both')

        # Поля для изображений
        self.main_images = product_data.get('main_images', [])
        self.additional_images = product_data.get('additional_images', [])
        self.all_images = product_data.get('all_images', [])
        self.total_images = product_data.get('total_images', 0)
        self.shuffle_images = product_data.get('shuffle_images', False)

        # Поля для доставки
        self.avito_delivery = product_data.get('avito_delivery', False)
        self.delivery_services = product_data.get('delivery_services', [])
        self.delivery_discount = product_data.get('delivery_discount', 'none')

        # Поле для мультиобъявления
        self.multioffer = product_data.get('multioffer', False)

        # Новые поля
        self.brand = product_data.get('brand', 'Не указан')
        self.size = product_data.get('size', '')
        self.condition = product_data.get('condition', '')
        self.sale_type = product_data.get('sale_type', '')
        self.placement_type = product_data.get('placement_type', '')
        self.placement_method = product_data.get('placement_method', '')
        self.cities = product_data.get('cities', [])
        self.quantity = product_data.get('quantity', 1)

        # Совместимость со старым кодом - создаем поле images
        # Если all_images не пустое, используем его, иначе создаем из main_images + additional_images
        if self.all_images:
            self.images = self.all_images
        else:
            self.images = self.main_images + self.additional_images
            self.all_images = self.images
            self.total_images = len(self.images)

        self.created_at = datetime.now()


class Database:
    def __init__(self):
        self.user_states: Dict[int, UserState] = {}
        self.products: List[Product] = []
        self.data_file = 'bot_data.json'

    async def load_data(self):
        """Загрузка данных из файла"""
        if os.path.exists(self.data_file):
            try:
                async with aiofiles.open(self.data_file, 'r', encoding='utf-8') as f:
                    data = await f.read()
                    if data:
                        json_data = json.loads(data)
                        # Загрузка состояний пользователей
                        for user_id_str, state_data in json_data.get('user_states', {}).items():
                            user_id = int(user_id_str)
                            self.user_states[user_id] = UserState(
                                user_id=user_id,
                                state=state_data.get('state', ''),
                                data=state_data.get('data', {})
                            )
                        # Загрузка товаров
                        for product_data in json_data.get('products', []):
                            # Генерируем новый GUID для старых записей без GUID
                            if 'product_id' not in product_data:
                                product_data['product_id'] = str(uuid.uuid4())

                            # Совместимость со старыми данными
                            if 'images' in product_data and 'all_images' not in product_data:
                                product_data['all_images'] = product_data['images']
                                product_data['total_images'] = len(product_data['images'])

                            # Обеспечиваем наличие всех полей
                            product_data.setdefault('main_images', [])
                            product_data.setdefault('additional_images', [])
                            product_data.setdefault('all_images', product_data.get('images', []))
                            product_data.setdefault('total_images', len(product_data['all_images']))
                            product_data.setdefault('shuffle_images', False)
                            product_data.setdefault('avito_delivery', False)
                            product_data.setdefault('delivery_services', [])
                            product_data.setdefault('delivery_discount', 'none')
                            product_data.setdefault('multioffer', False)
                            product_data.setdefault('brand', 'Не указан')
                            product_data.setdefault('size', '')
                            product_data.setdefault('condition', '')
                            product_data.setdefault('sale_type', '')
                            product_data.setdefault('placement_type', '')
                            product_data.setdefault('placement_method', '')
                            product_data.setdefault('cities', [])
                            product_data.setdefault('quantity', 1)

                            self.products.append(Product(
                                user_id=product_data['user_id'],
                                product_data=product_data
                            ))
            except Exception as e:
                print(f"Error loading data: {e}")

    async def save_data(self):
        """Сохранение данных в файл"""
        try:
            data = {
                'user_states': {
                    str(user_id): {
                        'state': state.state,
                        'data': state.data
                    }
                    for user_id, state in self.user_states.items()
                },
                'products': [
                    {
                        'user_id': product.user_id,
                        'product_id': product.product_id,
                        'title': product.title,
                        'description': product.description,
                        'price': product.price,
                        'price_type': product.price_type,
                        'price_min': product.price_min,
                        'price_max': product.price_max,
                        'category': product.category,
                        'category_name': product.category_name,
                        'contact_phone': product.contact_phone,
                        'display_phone': product.display_phone,
                        'contact_method': product.contact_method,

                        # Сохраняем все поля изображений
                        'main_images': product.main_images,
                        'additional_images': product.additional_images,
                        'all_images': product.all_images,
                        'total_images': product.total_images,
                        'shuffle_images': product.shuffle_images,

                        # Сохраняем поля доставки
                        'avito_delivery': product.avito_delivery,
                        'delivery_services': product.delivery_services,
                        'delivery_discount': product.delivery_discount,

                        # Сохраняем поле мультиобъявления
                        'multioffer': product.multioffer,

                        # Сохраняем новые поля
                        'brand': product.brand,
                        'size': product.size,
                        'condition': product.condition,
                        'sale_type': product.sale_type,
                        'placement_type': product.placement_type,
                        'placement_method': product.placement_method,
                        'cities': product.cities,
                        'quantity': product.quantity,

                        # Совместимость со старым кодом
                        'images': product.images,
                        'image_count': product.total_images,

                        'created_at': product.created_at.isoformat()
                    }
                    for product in self.products
                ]
            }
            async with aiofiles.open(self.data_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(data, ensure_ascii=False, indent=2))
        except Exception as e:
            print(f"Error saving data: {e}")

    # Методы для работы с состояниями пользователей
    async def set_user_state(self, user_id: int, state: str, data: dict = None):
        if user_id not in self.user_states:
            self.user_states[user_id] = UserState(user_id, state, data or {})
        else:
            self.user_states[user_id].state = state
            if data is not None:
                self.user_states[user_id].data = data
            self.user_states[user_id].updated_at = datetime.now()
        await self.save_data()

    async def get_user_state(self, user_id: int) -> Optional[UserState]:
        return self.user_states.get(user_id)

    async def clear_user_state(self, user_id: int):
        if user_id in self.user_states:
            del self.user_states[user_id]
            await self.save_data()

    # Методы для работы с товарами
    async def add_product(self, user_id: int, product_data: dict):
        try:
            # Гарантируем наличие GUID
            if 'product_id' not in product_data:
                product_data['product_id'] = str(uuid.uuid4())

            # Обеспечиваем наличие всех обязательных полей
            product_data.setdefault('main_images', [])
            product_data.setdefault('additional_images', [])
            product_data.setdefault('all_images', [])
            product_data.setdefault('total_images', 0)
            product_data.setdefault('shuffle_images', False)
            product_data.setdefault('avito_delivery', False)
            product_data.setdefault('delivery_services', [])
            product_data.setdefault('delivery_discount', 'none')
            product_data.setdefault('multioffer', False)
            product_data.setdefault('brand', 'Не указан')
            product_data.setdefault('size', '')
            product_data.setdefault('condition', '')
            product_data.setdefault('sale_type', '')
            product_data.setdefault('placement_type', '')
            product_data.setdefault('placement_method', '')
            product_data.setdefault('cities', [])
            product_data.setdefault('quantity', 1)

            # Совместимость со старым кодом
            if not product_data['all_images'] and (
                    'main_images' in product_data or 'additional_images' in product_data):
                product_data['all_images'] = product_data.get('main_images', []) + product_data.get('additional_images',
                                                                                                    [])
                product_data['total_images'] = len(product_data['all_images'])

            product = Product(user_id, product_data)
            self.products.append(product)
            await self.save_data()
            return product
        except Exception as e:
            print(f"Error in add_product: {e}")
            raise

    async def get_user_products(self, user_id: int) -> List[Product]:
        return [p for p in self.products if p.user_id == user_id]

    async def delete_product(self, user_id: int, product_index: int):
        user_products = await self.get_user_products(user_id)
        if 0 <= product_index < len(user_products):
            product_to_delete = user_products[product_index]
            self.products.remove(product_to_delete)
            await self.save_data()
            return True
        return False


# Глобальный экземпляр базы данных
db = Database()