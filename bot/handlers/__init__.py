from .start_handlers import StartHandlers
from .product_handlers import ProductHandlers
from .image_handlers import ImageHandlers
from .location_handlers import LocationHandlers
from .delivery_handlers import DeliveryHandlers
from .common_handlers import CommonHandlers


def initialize_handlers(db):
    """Инициализировать все обработчики с передачей базы данных"""
    start_handlers = StartHandlers(db)
    product_handlers = ProductHandlers(db)
    image_handlers = ImageHandlers()
    location_handlers = LocationHandlers(db)
    delivery_handlers = DeliveryHandlers(db)
    common_handlers = CommonHandlers(db)  # ✅ Теперь db передается

    return [
        start_handlers.router,
        product_handlers.router,
        image_handlers.router,
        location_handlers.router,
        delivery_handlers.router,
        common_handlers.router
    ]