from aiogram.fsm.state import State, StatesGroup

class ProductStates(StatesGroup):
    waiting_for_category = State()
    waiting_for_subcategory = State()
    waiting_for_title = State()
    waiting_for_description = State()
    waiting_for_price_type = State()
    waiting_for_price = State()
    waiting_for_price_range = State()
    waiting_for_phone = State()
    waiting_for_contact_method = State()
    waiting_for_main_images = State()
    waiting_for_additional_images = State()
    waiting_for_shuffle_images = State()
    waiting_for_avito_delivery = State()
    waiting_for_delivery_services = State()