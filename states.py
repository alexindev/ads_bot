from aiogram.dispatcher.filters.state import State, StatesGroup

class Job(StatesGroup):
    image = State()
    text = State()
