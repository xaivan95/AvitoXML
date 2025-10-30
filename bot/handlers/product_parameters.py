# product_parameters.py
BAG_PARAMETERS = {
    "bag_type": {
        "name": "Вид сумки",
        "required": True,
        "values": [
            ("👜 Через плечо", "shoulder"),
            ("🎒 Кросс-боди", "crossbody"),
            ("🏃 Спортивная", "sports"),
            ("👛 Клатч", "clutch"),
            ("💼 Поясная", "waist"),
            ("🛍️ Шопер", "shopper"),
            ("🏖️ Пляжная", "beach"),
            ("👜 С ручками", "with_handles"),
            ("🎀 Аксессуар для сумки", "accessory")
        ]
    },
    "bag_gender": {
        "name": "Для кого",
        "required": True,
        "values": [
            ("👩 Женщины", "women"),
            ("👨 Мужчины", "men"),
            ("👥 Унисекс", "unisex")
        ]
    }
}

def get_bag_parameters():
    """Получить параметры для сумок"""
    return BAG_PARAMETERS

def is_bag_category(category_name: str) -> bool:
    """Проверяет, относится ли категория к сумкам"""
    bag_keywords = [
        "сумк", "рюкзак", "чемодан", "портфель", "клатч", "шопер",
        "баг", "bag", "backpack", "clutch", "shopper"
    ]
    category_lower = category_name.lower()
    return any(keyword in category_lower for keyword in bag_keywords)