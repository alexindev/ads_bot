from aiogram.dispatcher.filters.state import State, StatesGroup

class Job(StatesGroup):
    image = State()
    text = State()

class User(StatesGroup):
    first_report = State()
    start_working = State()
