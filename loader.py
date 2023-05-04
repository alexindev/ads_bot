from aiogram import types, Dispatcher, Bot
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from database import Database
from config import TOKEN, ADMINS
from states import *
from kb import *

bot = Bot(TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
base = Database()


@dp.message_handler(commands=['start'])
async def start_command_handler(message: types.Message):
    await bot.send_message(message.from_user.id,
                           text='Привет! Это бот. Тут приветственное сообщение',
                           reply_markup=start)


@dp.callback_query_handler(lambda c: c.data == 'cities_list')
async def choise_city(callback: types.CallbackQuery):
    """Вывести все города в инлайн кнопках"""
    await callback.answer()
    cities = get_cities_keyboard(base)
    await bot.edit_message_text(chat_id=callback.from_user.id,
                                message_id=callback.message.message_id,
                                text='Выберите город:',
                                reply_markup=cities)


@dp.callback_query_handler(lambda c: c.data == 'new_city')
async def new_city(callback: types.CallbackQuery, state: FSMContext):
    """Добавить новый город"""
    await callback.answer()
    await state.set_state(City.city)

    await bot.edit_message_text(chat_id=callback.from_user.id,
                                message_id=callback.message.message_id,
                                text='Название нового города:',
                                reply_markup=back)


@dp.message_handler(state=City.city)
async def process_new_city(message: types.Message, state: FSMContext):
    """Обработчик для получения названия нового города"""
    city = message.text

    if not base.get_city(city):
        base.create_table(city)
        await bot.send_message(message.from_user.id,
                               text=f'Город "{city}" добавлен!',
                               reply_markup=city_add)
        await state.finish()
    else:
        await bot.send_message(chat_id=message.from_user.id,
                               text=f'Город "{city}" уже добавлен!',
                               reply_markup=back)
        await state.finish()


@dp.callback_query_handler(lambda c: c.data.startswith('back'), state='*')
async def cancel_fsm(callback: types.CallbackQuery, state: FSMContext):
    """Выйти из FSM"""
    await callback.answer()
    await state.finish()
    if callback.data == 'back':
        await bot.edit_message_text(chat_id=callback.from_user.id,
                                    message_id=callback.message.message_id,
                                    text='Привет! Это бот. Тут приветственное сообщение',
                                    reply_markup=start)
    else:
        await bot.send_message(chat_id=callback.from_user.id,
                               text='Привет! Это бот. Тут приветственное сообщение',
                               reply_markup=start)


@dp.message_handler(commands=['config'])
async def config(message: types.Message):
    """Меню настроек"""
    if message.from_user.id in ADMINS:
        await bot.send_message(chat_id=message.from_user.id,
                               text='Меню настроек:',
                               reply_markup=config_kb)
    else:
        await bot.send_message(chat_id=message.from_user.id,
                               text='🚫 Нет доступа 🚫',
                               reply_markup=back)


@dp.callback_query_handler(lambda c: c.data.startswith('city_'))
async def city_callback(callback: types.CallbackQuery, state: FSMContext):
    """Работа с отдельным городом"""
    await callback.answer()
    city_name = callback.data.replace('city_', '')

    async with state.proxy() as data:
        data['current_city'] = city_name

    if callback.from_user.id in ADMINS:
        await bot.edit_message_text(chat_id=callback.from_user.id,
                                    message_id=callback.message.message_id,
                                    text=f'Выбран город: {city_name}',
                                    reply_markup=admim_city_config)
    else:
        await bot.edit_message_text(chat_id=callback.from_user.id,
                                    message_id=callback.message.message_id,
                                    text=f'Выбран город: {city_name}. Приступить к работе?',
                                    reply_markup=ready_to_work)


@dp.callback_query_handler(lambda c: c.data == 'jobs')
async def jobs(callback: types.CallbackQuery):
    """Работа с заданиями"""
    await callback.answer()
    await bot.edit_message_text(chat_id=callback.from_user.id,
                                message_id=callback.message.message_id,
                                text='Введите операцию:',
                                reply_markup=jobs_config)


@dp.callback_query_handler(lambda c: c.data == 'delete_city', state='*')
async def delete_city(callback: types.CallbackQuery, state: FSMContext):
    """Удаление города"""
    data = await state.get_data()
    current_city = data.get('current_city')

    if base.delete_city(current_city):
        await bot.edit_message_text(chat_id=callback.from_user.id,
                                    message_id=callback.message.message_id,
                                    text=f'Город: {current_city} удален',
                                    reply_markup=back)
    else:
        await bot.edit_message_text(chat_id=callback.from_user.id,
                                    message_id=callback.message.message_id,
                                    text=f'Ошибка удаления города: {current_city}',
                                    reply_markup=back)
    await state.finish()


@dp.callback_query_handler(lambda c: c.data == 'new_job')
async def new_job(callback: types.CallbackQuery, state: FSMContext):
    """Добавление новых заданий"""
    await callback.answer()
    await bot.send_message(callback.from_user.id,
                           text='Отправьте картинку:',
                           reply_markup=back)
    await state.set_state(Job.image)


@dp.message_handler(content_types=types.ContentType.PHOTO, state=Job.image)
async def process_image(message: types.Message, state: FSMContext):
    """Получение картинки"""
    async with state.proxy() as data:
        data['image'] = message.photo[0].file_id

    await state.set_state(Job.text)
    await message.reply('Введите идентификатор задания:')


@dp.message_handler(state=Job.text)
async def save_job(message: types.Message, state: FSMContext):
    """Идентификатор для задания и сохранение в базу данных"""
    async with state.proxy() as data:
        data['text'] = message.text
        current_city = data.get('current_city')
        if not base.get_job(current_city, data['text']):
            base.new_job(current_city, data['image'], data['text'], status=1)
            await bot.send_message(message.from_user.id, 'Задание добавлено',
                                   reply_markup=job_add)
        else:
            await bot.send_message(message.from_user.id,
                                   f'Задание с id: {data["text"]} уже добавлено',
                                   reply_markup=job_add)
        await state.finish()


@dp.callback_query_handler(lambda c: c.data == 'get_job')
async def get_jobs(callback: types.CallbackQuery, state: FSMContext):
    """Получить все задания"""
    await callback.answer()
    state_data = await state.get_data()
    city = state_data.get('current_city')
    jobs_kb = get_jobs_kb(base, city)

    await bot.edit_message_text(chat_id=callback.from_user.id,
                                message_id=callback.message.message_id,
                                text='Все задания:',
                                reply_markup=jobs_kb)


@dp.callback_query_handler(lambda c: c.data.startswith('job_'))
async def jods_view(callback: types.CallbackQuery, state: FSMContext):
    """Работа с выбранным заданием"""
    await callback.answer()

    job_id = callback.data.replace('job_', '')
    state_data = await state.get_data()
    city = state_data.get('current_city')

    async with state.proxy() as data:
        data['job_id'] = job_id

    photo = base.get_photo(city, job_id)

    await bot.send_photo(chat_id=callback.from_user.id,
                         photo=photo[0],
                         caption=f'Выбрано задание с идентификатором {job_id}',
                         reply_markup=kb_job_photo)


@dp.callback_query_handler(lambda c: c.data == 'delete_job_photo', state='*')
async def delete_job_fucn(callback: types.CallbackQuery, state: FSMContext):
    """Удалить задание"""
    await callback.answer()
    data = await state.get_data()
    city = data.get('current_city')
    job_id = data.get('job_id')
    base.delete_job(city, job_id)

    await bot.send_message(chat_id=callback.from_user.id,
                           text=f'Задание с идентификатором "{job_id}" удалено',
                           reply_markup=delete_job)


@dp.callback_query_handler(lambda c: c.data == 'start_job', state='*')
async def start_work(callback: types.CallbackQuery, state: FSMContext):
    """Подготовка к работе пользователя"""
    await callback.answer()
    await bot.edit_message_text(chat_id=callback.from_user.id,
                                message_id=callback.message.message_id,
                                text='Перед началом работы необходимо отправить фотоотчет\n'
                                     'Прикрепите фото к этому сообщению',
                                reply_markup=back)
    await state.set_state(User.first_report)


@dp.message_handler(content_types=types.ContentType.PHOTO, state=User.first_report)
async def first_report(message: types.Message, state: FSMContext):
    """Получить фотоотчет о начале работы"""
    async with state.proxy() as data:
        data['first_report_image'] = message.photo[0].file_id

    """Отправить фото в канал по отчетам"""

    await state.set_state(User.start_working)
    await bot.send_message(chat_id=message.from_user.id,
                           text='Фото добавлено. Нажмите "Начать", чтобы приступить к работе',
                           reply_markup=start_working
                           )


@dp.callback_query_handler(lambda c: c.data == 'start_work', state=User.start_working)
async def started_work(callback: types.CallbackQuery, state: FSMContext):
    """Ожидание получения финального отчета"""
    await callback.answer()
    await bot.edit_message_text(chat_id=callback.from_user.id,
                                message_id=callback.message.message_id,
                                text='После завершения работы необходимо написать отчет по шаблону из примера на фото\n',
                                )
    with open('images/template.jpg', 'rb') as photo:
        await bot.send_photo(chat_id=callback.from_user.id, photo=types.InputFile(photo), reply_markup=back)
