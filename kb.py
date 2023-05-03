from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


start = InlineKeyboardMarkup(row_width=1).add(
    InlineKeyboardButton(text='Выбрать город', callback_data='city'),
    InlineKeyboardButton(text='Добавить город', callback_data='new_city')
)

back = InlineKeyboardMarkup(row_width=1).add(
    InlineKeyboardButton(text='Назад', callback_data='back')
)

def get_cities_keyboard(db):
    """Кнопки со всеми городами"""
    cities = db.get_cities()
    kb = InlineKeyboardMarkup(row_width=1)
    for city in cities:
        kb.add(InlineKeyboardButton(text=city[0], callback_data=f"city_{city[0]}"))
    return kb
