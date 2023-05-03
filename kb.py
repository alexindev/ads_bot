from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


start = InlineKeyboardMarkup(row_width=1).add(
    InlineKeyboardButton(text='Выбрать город', callback_data='cities_list'),
)

back = InlineKeyboardMarkup(row_width=1).add(
    InlineKeyboardButton(text='Назад', callback_data='back')
)

config_kb = InlineKeyboardMarkup(row_width=1).add(
    InlineKeyboardButton(text='Добавить город', callback_data='new_city'),
    InlineKeyboardButton(text='Другие настройки', callback_data='other_config'),
    InlineKeyboardButton(text='Назад', callback_data='back')
)

job_start = InlineKeyboardMarkup(row_width=1).add(
    InlineKeyboardButton(text="Начать", callback_data='job_start'),
    InlineKeyboardButton(text='Назад', callback_data='back')
)

admim_city_config = InlineKeyboardMarkup(row_width=1).add(
    InlineKeyboardButton(text='Добавить задания', callback_data='new_job'),
    InlineKeyboardButton(text='Удалить город', callback_data='delete_city'),
    InlineKeyboardButton(text='Назад', callback_data='back')
)

def get_cities_keyboard(db):
    """Кнопки со всеми городами"""
    cities = db.get_cities()
    kb = InlineKeyboardMarkup(row_width=1)
    for city in cities:
        kb.add(InlineKeyboardButton(text=city[0], callback_data=f"city_{city[0]}"))
    kb.add(InlineKeyboardButton(text='Назад', callback_data='back'))
    return kb
