# bot/states.py
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
    waiting_for_delivery_discount = State()
    waiting_for_delivery_discount_percent = State()  # НОВОЕ: для ввода процента скидки
    waiting_for_multioffer = State()
    waiting_for_brand = State()
    waiting_for_size = State()
    waiting_for_condition = State()
    waiting_for_sale_type = State()
    waiting_for_placement_type = State()
    waiting_for_placement_method = State()
    waiting_for_cities = State()
    waiting_for_city_input = State()  # Для поштучного ввода городов
    waiting_for_city_confirmation = State()  # Для подтверждения города
    waiting_for_quantity = State()
    waiting_for_metro_city = State()
    waiting_for_metro_quantity = State()
    # Добавляем новое состояние для даты старта
    waiting_for_start_date = State()
    waiting_for_start_time = State()  # Добавляем новое состояние для времени
    waiting_for_bag_type = State()      # Ожидание выбора вида сумки
    waiting_for_bag_gender = State()    # Ожидание выбора назначения
    waiting_for_bag_color = State()      # Новое: ожидание выбора цвета
    waiting_for_bag_material = State()   # Новое: ожидание выбора материала
    waiting_for_shoe_color = State()        # Ожидание ввода цвета
    waiting_for_shoe_material = State()     # Ожидание выбора материала
    waiting_for_shoe_manufacturer_color = State() # Ожидание ввода цвета от производителя
    waiting_for_accessory_color = State()      # Ожидание выбора цвета
    waiting_for_accessory_gender = State()     # Ожидание выбора "Для кого"
    waiting_for_subsubcategory = State()  # Ожидание выбора подкатегории третьего уровня
    waiting_for_clothing_size = State()           # Ожидание выбора размера одежды
    waiting_for_clothing_color = State()          # Ожидание выбора цвета одежды
    waiting_for_clothing_material = State()       # Ожидание выбора материала одежды
    waiting_for_clothing_manufacturer_color = State()  # Ожидание ввода цвета от производителя