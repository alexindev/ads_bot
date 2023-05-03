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


@dp.callback_query_handler(lambda c: c == 'back')
async def cancel(callback: types.CallbackQuery):
    """Возврат на главное меню"""
    await callback.answer()
    await bot.edit_message_text(chat_id=callback.from_user.id,
                                message_id=callback.message.message_id,
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
    await state.set_state('new_city')
    await bot.edit_message_text(chat_id=callback.from_user.id,
                                message_id=callback.message.message_id,
                                text='Название нового города:',
                                reply_markup=back)


@dp.message_handler(state='new_city')
async def process_new_city(message: types.Message, state: FSMContext):
    """Обработчик для получения названия нового города"""
    city = message.text

    if not base.get_city(city):
        base.create_table(city)
        await bot.send_message(message.from_user.id,
                               text=f'Город {city} добавлен!',
                               reply_markup=city_add)
        await state.finish()
    else:
        await bot.send_message(chat_id=message.from_user.id,
                               text=f'Город {city} уже добавлен!',
                               reply_markup=back)
        await state.finish()


@dp.callback_query_handler(lambda c: c.data == 'back', state='*')
async def cancel_fsm(callback: types.CallbackQuery, state: FSMContext):
    """Выйти из FSM"""
    await state.finish()
    await bot.edit_message_text(chat_id=callback.from_user.id,
                                message_id=callback.message.message_id,
                                text='Привет! Это бот. Тут приветственное сообщение',
                                reply_markup=start)


@dp.message_handler(commands=['config'])
async def config(message: types.Message):
    """Меню настроек"""
    if message.from_user.id in ADMINS:
        await bot.send_message(chat_id=message.from_user.id,
                               text='Меню настроек:',
                               reply_markup=config_kb)


@dp.callback_query_handler(lambda c: c.data.startswith('city_'))
async def city_callback(callback: types.CallbackQuery, state: FSMContext):
    """Работа с отдельным городом"""
    await callback.answer()
    city_name = callback.data.replace('city_', '')

    if callback.from_user.id in ADMINS:
        await state.update_data(current_city=city_name)
        await bot.edit_message_text(chat_id=callback.from_user.id,
                                    message_id=callback.message.message_id,
                                    text=f'Выбран город: {city_name}',
                                    reply_markup=admim_city_config)
    else:
        await bot.edit_message_text(chat_id=callback.from_user.id,
                                    message_id=callback.message.message_id,
                                    text=f'Выбран город: {city_name}. Приступить к работе?',
                                    reply_markup=job_start)


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


@dp.callback_query_handler(lambda c: c.data == 'new_job')
async def new_job(callback: types.CallbackQuery, state: FSMContext):
    """Добавление новых заданий"""
    await callback.answer()
    async with state.proxy() as data:
        data['city'] = callback.message.text.split(' ')[-1]
    await bot.send_message(callback.from_user.id,
                           text='Отправьте картинку:',
                           reply_markup=back)
    await state.set_state(Job.image)


@dp.message_handler(content_types=types.ContentType.PHOTO, state=Job.image)
async def process_image(message: types.Message, state: FSMContext):
    """Получение картинки"""
    async with state.proxy() as data:
        data['image'] = message.photo[0].file_id
    await message.reply('Введите идентификатор задания:')
    await state.set_state(Job.text)


@dp.message_handler(state=Job.text)
async def save_job(message: types.Message, state: FSMContext):
    """Идентификатор для задания и сохранение в базу данных"""
    async with state.proxy() as data:
        data['text'] = message.text

    await state.finish()
    if not base.get_job(data['city'], data['text']):
        base.new_job(data['city'], data['image'], data['text'], status=1)
        await bot.send_message(message.from_user.id, 'Скрин добавлен',
                               reply_markup=back)
    else:
        await bot.send_message(message.from_user.id,
                               f'Скрин с id: {data["text"]} уже добавлен',
                               reply_markup=back)
