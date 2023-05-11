from aiogram.dispatcher.filters.state import State, StatesGroup

class Job(StatesGroup):
    image = State()
    text = State()

class User(StatesGroup):
    start_working = State()
    make_report = State()
    continue_work = State()
    end_job = State()

class City(StatesGroup):
    city = State()

class Admin(StatesGroup):
    job = State()
    job_operation = State()
    jobs_list = State()
    job_delete = State()