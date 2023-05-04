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

ready_to_work = InlineKeyboardMarkup(row_width=2).add(
    InlineKeyboardButton(text="Да", callback_data='start_job'),
    InlineKeyboardButton(text='Отмена', callback_data='back')
)

start_working = InlineKeyboardMarkup(row_width=1).add(
    InlineKeyboardButton(text='Начать', callback_data='start_work'),
    InlineKeyboardButton(text='Отмена', callback_data='back')
)

city_add = InlineKeyboardMarkup(row_width=1).add(
    InlineKeyboardMarkup(text='Добавить город', callback_data='new_city'),
    InlineKeyboardButton(text='Назад', callback_data='back')
)

admim_city_config = InlineKeyboardMarkup(row_width=1).add(
    InlineKeyboardButton(text='Задания', callback_data='jobs'),
    InlineKeyboardButton(text='Удалить город', callback_data='delete_city'),
    InlineKeyboardButton(text='Отмена', callback_data='back')
)

jobs_config = InlineKeyboardMarkup(row_width=1).add(
    InlineKeyboardButton(text='Получить все задания', callback_data='get_job'),
    InlineKeyboardButton(text='Добавить', callback_data='new_job'),
    InlineKeyboardButton(text='Отмена', callback_data='back')
)

first_report = InlineKeyboardMarkup(row_width=1).add(
    InlineKeyboardButton(text='Сделать фотоотчет', callback_data='first_report'),
    InlineKeyboardButton(text='Отмена', callback_data='back')
)

job_add = InlineKeyboardMarkup(row_width=1).add(
    InlineKeyboardButton(text='Добавить новое задание', callback_data='new_job'),
    InlineKeyboardButton(text='Назад', callback_data='back')
)

kb_job_photo = InlineKeyboardMarkup(row_width=1).add(
    InlineKeyboardButton(text='Удалить', callback_data='delete_job_photo'),
    InlineKeyboardButton(text='Назад', callback_data='back_new')
)

delete_job = InlineKeyboardMarkup(row_width=1).add(
    InlineKeyboardButton(text='Назад', callback_data='get_job'),
    InlineKeyboardButton(text='На главную', callback_data='back')
)

def get_cities_keyboard(db):
    """Кнопки со всеми городами"""
    cities = db.get_cities()
    kb = InlineKeyboardMarkup(row_width=1)
    for city in cities:
        kb.add(InlineKeyboardButton(text=city[0], callback_data=f"city_{city[0]}"))
    kb.add(InlineKeyboardButton(text='Назад', callback_data='back'))
    return kb

def get_jobs_kb(db, city):
    """Кнопки со всеми заданиями"""
    jobs = db.get_all_jobs(city)
    kb = InlineKeyboardMarkup(row_width=3)
    for job in jobs:
        kb.insert(InlineKeyboardButton(text=job[0], callback_data=f"job_{job[0]}"))
    kb.add(InlineKeyboardButton(text='Назад', callback_data='back'))
    return kb
