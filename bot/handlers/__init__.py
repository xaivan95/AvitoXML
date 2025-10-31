# bot/handlers/__init__.py
from .start_handlers import StartHandlers
from .product_handlers import ProductHandlers
from .image_handlers import ImageHandlers
from .location_handlers import LocationHandlers
from .delivery_handlers import DeliveryHandlers
from .common_handlers import CommonHandlers

# Создаем все обработчики
start_handlers = StartHandlers()
product_handlers = ProductHandlers()
image_handlers = ImageHandlers()
location_handlers = LocationHandlers()
delivery_handlers = DeliveryHandlers()
common_handlers = CommonHandlers()

# Объединяем все роутеры
def get_all_routers():
    """Получить все роутеры"""
    routers = [
        start_handlers.router,
        product_handlers.router,
        image_handlers.router,
        location_handlers.router,
        delivery_handlers.router,
        common_handlers.router
    ]
    return routers