import asyncio
import time

import aiogram.utils.exceptions
from aiogram import types, Dispatcher, Bot
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from loguru import logger

from db.database import Database
from config import *
from state.states import *
from keyboard.kb import *


bot = Bot(TOKEN, parse_mode='HTML')
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
base = Database()


@dp.message_handler(commands=['start'])
async def start_command_handler(message: types.Message):
    if message.from_user.id in ADMINS or await check_subsciber(message.from_user.id):
        await bot.send_message(message.from_user.id,
                               text='Привет! Это бот, который поможет получить маршрут для работы!',
                               reply_markup=start)

@dp.message_handler(commands=['help'])
async def help_cmd(message: types.Message):
    if message.from_user.id in ADMINS or await check_subsciber(message.from_user.id):
        await bot.send_message(message.from_user.id,
                               text='<b>Памятки для работы с ботом:</b>\n\n'
                                    'Для начала работы необходимо в главном меню выбрать свой город <b>кнопка "Выбрать город"</b>\n\n'
                                    'После подтверждения начала работы назначится первый доступный маршрут\n\n'
                                    'До начала работы будет интервал <b>5 часов</b>. Если за это время не приступить к работе, маршрут будет отменен\n\n'
                                    'Перед началом работы, необходимо отправить фотоотчет со стартового адреса. <b>Прикрепить фото к соответсвующему сообщению</b>\n\n'
                                    'После каждого прохождения каждого <b>5 дома</b> в маршруте нужно написать отчет от проделанной работе <b>кнопка "Отправить отчет"</b>\n\n'
                                    'Для добавления нового отчета <b>кнопка "Отправить новый отчет"</b>\n\n'
                                    'После отправки последнего отчета <b>кнопка "Завершить маршрут"</b>',

                               reply_markup=back)


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
    if callback.data == 'back':
        await bot.edit_message_text(chat_id=callback.from_user.id,
                                    message_id=callback.message.message_id,
                                    text='Привет! Это бот, который поможет получить маршрут для работы!',
                                    reply_markup=start)
        await state.finish()

    elif callback.data == 'back_new':
        await bot.send_message(chat_id=callback.from_user.id,
                               text='Привет! Это бот, который поможет получить маршрут для работы!',
                               reply_markup=start)
        await state.finish()

    elif callback.data == 'back_job':
        async with state.proxy() as data:
            city = data.get('current_city')
            job_id = data.get('job_id')

        base.update_job_status(city, job_id, status=1)
        await bot.send_message(chat_id=callback.from_user.id,
                               text='Маршрут отменен',
                               reply_markup=start)

        group = await check_subscriber_group(callback.from_user.id)
        if group == 'GROUP1':
            await bot.send_message(chat_id=GROUP_CHAT_ID[0],
                                   text=f'Работник <a href="tg://user?id={callback.from_user.id}">{callback.from_user.full_name}</a> отменил маршрут\n'
                                        f'Город: {city}\n'
                                        f'Маршрут: # {job_id}\n'
                                   )
        elif group == 'GROUP2':
            await bot.send_message(chat_id=GROUP_CHAT_ID[1],
                                   text=f'Работник <a href="tg://user?id={callback.from_user.id}">{callback.from_user.full_name}</a> отменил маршрут\n'
                                        f'Город: {city}\n'
                                        f'Маршрут: # {job_id}\n'
                                   )
        await state.finish()


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

    async with state.proxy() as data:
        data['current_city'] = city_name

    if callback.from_user.id in ADMINS:
        await bot.edit_message_text(chat_id=callback.from_user.id,
                                    message_id=callback.message.message_id,
                                    text=f'Выбран город: {city_name}',
                                    reply_markup=admim_city_config)
        await state.set_state(Admin.job)
    else:
        await bot.edit_message_text(chat_id=callback.from_user.id,
                                    message_id=callback.message.message_id,
                                    text=f'Выбран город: {city_name}. Приступить к работе?',
                                    reply_markup=ready_to_work)


@dp.callback_query_handler(lambda c: c.data == 'delete_city', state=Admin.job)
async def delete_city(callback: types.CallbackQuery, state: FSMContext):
    """Удаление города"""
    await callback.answer()

    async with state.proxy() as data:
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


@dp.callback_query_handler(lambda c: c.data == 'start_job', state='*')
async def start_work(callback: types.CallbackQuery, state: FSMContext):
    """Подготовка к работе"""
    await callback.answer()

    async with state.proxy() as data:
        city = data.get('current_city')

    job = base.get_job_photo_id(city, status=1)

    if job:
        async with state.proxy() as data:
            data['job_id'] = job[1]

        base.update_job_status(city, job[1], status=0)
        await bot.send_photo(chat_id=callback.from_user.id,
                             photo=job[0],
                             caption=f'Вам присвоен участок # {job[1]}\n'
                                     'Перед началом работы необходимо отправить фотоотчет.\n'
                                     'Прикрепите фото к этому сообщению',
                             reply_markup=back_job_cancel)
        await state.set_state(User.first_report)

        # Время на принятие решения работником
        asyncio.create_task(check_state_timeout(state, city, job[1], callback, params='start'))

        asyncio.create_task(job_timeout(state, city, job[1], callback))

    else:
        await bot.edit_message_text(chat_id=callback.from_user.id,
                                    message_id=callback.message.message_id,
                                    text='На данный момент нет доступных маршрутов, повторите попытку позже',
                                    reply_markup=back)
        base.update_status(city, status=1)
        await state.finish()


@dp.message_handler(content_types=types.ContentType.PHOTO, state=User.first_report)
async def first_report(message: types.Message, state: FSMContext):
    """Получить фотоотчет о начале работы"""
    async with state.proxy() as data:
        data['first_report_image'] = message.photo[0].file_id
        city = data.get('current_city')
        job_id = data.get('job_id')

    await bot.send_message(chat_id=message.from_user.id,
                           text='Фото добавлено. Нажмите "Начать", чтобы приступить к работе',
                           reply_markup=start_working
                           )

    # Время на принятие решения работником
    asyncio.create_task(check_state_timeout(state, city, job_id, message, params='confirm'))

    await state.set_state(User.start_working)


@dp.callback_query_handler(lambda c: c.data == 'start_work', state=User.start_working)
async def started_work(callback: types.CallbackQuery, state: FSMContext):
    """Начало работы работника"""
    await callback.answer()
    async with state.proxy() as data:
        job_id = data.get('job_id')
        job_photo = data.get('first_report_image')
        city = data.get('current_city')

    group = await check_subscriber_group(callback.from_user.id)
    if group == 'GROUP1':
        await bot.send_photo(chat_id=GROUP_CHAT_ID[0],
                             photo=job_photo,
                             caption=f'Работник <a href="tg://user?id={callback.from_user.id}">{callback.from_user.full_name}</a> приступил к работе\n'
                                     f'Город: {city}\n'
                                     f'Назначен участок: # {job_id}')
    elif group == 'GROUP2':
        await bot.send_photo(chat_id=GROUP_CHAT_ID[1],
                             photo=job_photo,
                             caption=f'Работник <a href="tg://user?id={callback.from_user.id}">{callback.from_user.full_name}</a> приступил к работе\n'
                                     f'Город: {city}\n'
                                     f'Назначен участок: # {job_id}')

    await bot.edit_message_text(chat_id=callback.from_user.id,
                                message_id=callback.message.message_id,
                                text='После каждого 5 дома необходимо написать отчет (текст) по шаблону из фото\n'
                                )

    with open('images/template.jpg', 'rb') as photo:
        await bot.send_photo(chat_id=callback.from_user.id,
                             photo=types.InputFile(photo),
                             reply_markup=user_send_report)
    await state.set_state(User.make_report)


@dp.callback_query_handler(lambda c: c.data == 'send_report', state=User.make_report)
async def report_work(callback: types.CallbackQuery, state: FSMContext):
    """Работа с отчетами работников"""
    await callback.answer()

    await bot.send_message(chat_id=callback.from_user.id,
                           text='Отправьте сообщение с отчетом',
                           reply_markup=back_new)
    await state.set_state(User.send_report)


@dp.message_handler(state=User.send_report)
async def save_report(message: types.Message, state: FSMContext):
    """Текстовый отчет от работника. Пересылка в канал"""
    report = message.text
    async with state.proxy() as data:
        job_id = data.get('job_id')
        city = data.get('current_city')

    group = await check_subscriber_group(message.from_user.id)
    if group == 'GROUP1':
        await bot.send_message(chat_id=GROUP_CHAT_ID[0],
                               text=f'Отчет от работника <a href="tg://user?id={message.from_user.id}">{message.from_user.full_name}</a>\n'
                                    f'Город: {city}\n'
                                    f'Маршрут: # {job_id}\n'
                                    f'{report}')
    elif group == 'GROUP2':
        await bot.send_message(chat_id=GROUP_CHAT_ID[1],
                               text=f'Отчет от работника <a href="tg://user?id={message.from_user.id}">{message.from_user.full_name}</a>\n'
                                    f'Город: {city}\n'
                                    f'Маршрут: # {job_id}\n'
                                    f'{report}')

    await bot.send_message(message.from_user.id,
                           text='Отчет принят. Выберите действие: ',
                           reply_markup=user_new_report
                           )
    await state.set_state(User.make_report)


@dp.callback_query_handler(lambda c: c.data == 'end_work_job', state=User.make_report)
async def end_work(callback: types.CallbackQuery, state: FSMContext):
    """Завершается маршрут"""
    await callback.answer()

    async with state.proxy() as data:
        job_id = data.get('job_id')
        city = data.get('current_city')

    group = await check_subscriber_group(callback.from_user.id)
    if group == 'GROUP1':
        await bot.send_message(chat_id=GROUP_CHAT_ID[0],
                               text=f'Работник <a href="tg://user?id={callback.from_user.id}">{callback.from_user.full_name}</a> завершил маршрут\n'
                                    f'Город: {city}\n'
                                    f'Маршрут: # {job_id}\n'
                               )
    elif group == 'GROUP2':
        await bot.send_message(chat_id=GROUP_CHAT_ID[1],
                               text=f'Работник <a href="tg://user?id={callback.from_user.id}">{callback.from_user.full_name}</a> завершил маршрут\n'
                                    f'Город: {city}\n'
                                    f'Маршрут: # {job_id}\n'
                               )

    await bot.edit_message_text(chat_id=callback.from_user.id,
                                message_id=callback.message.message_id,
                                text='Маршрут завершен',
                                reply_markup=back)
    await state.set_state(User.end_job)


@dp.callback_query_handler(lambda c: c.data == 'jobs', state=Admin.job)
async def jobs(callback: types.CallbackQuery, state: FSMContext):
    """Работа с заданиями для админов"""
    await callback.answer()
    await bot.edit_message_text(chat_id=callback.from_user.id,
                                message_id=callback.message.message_id,
                                text='Выберите операцию:',
                                reply_markup=jobs_config)
    await state.set_state(Admin.job_operation)


@dp.callback_query_handler(lambda c: c.data == 'get_job', state='*')
async def get_jobs(callback: types.CallbackQuery, state: FSMContext):
    """Получить все задания"""
    await callback.answer()
    async with state.proxy() as data:
        city = data.get('current_city')

    jobs_kb = get_jobs_kb(base, city)

    await bot.edit_message_text(chat_id=callback.from_user.id,
                                message_id=callback.message.message_id,
                                text='Все маршруты:',
                                reply_markup=jobs_kb)
    await state.set_state(Admin.jobs_list)


@dp.callback_query_handler(lambda c: c.data.startswith('job_'), state=Admin.jobs_list)
async def jods_view(callback: types.CallbackQuery, state: FSMContext):
    """Работа с выбранным маршрутом"""
    await callback.answer()

    job_id = callback.data.replace('job_', '')

    async with state.proxy() as data:
        data['job_id'] = job_id
        city = data.get('current_city')

    photo = base.get_photo(city, job_id)

    await bot.send_photo(chat_id=callback.from_user.id,
                         photo=photo[0],
                         caption=f'Выбран маршрут с идентификатором {job_id}',
                         reply_markup=kb_job_photo)
    await state.set_state(Admin.job_delete)


@dp.callback_query_handler(lambda c: c.data == 'delete_job_photo', state=Admin.job_delete)
async def delete_job_fucn(callback: types.CallbackQuery, state: FSMContext):
    """Удалить маршрут"""
    await callback.answer()

    async with state.proxy() as data:
        city = data.get('current_city')
        job_id = data.get('job_id')

    base.delete_job(city, job_id)

    await bot.send_message(chat_id=callback.from_user.id,
                           text=f'Маршрут с идентификатором "{job_id}" удален',
                           reply_markup=delete_job)
    await state.set_state(Admin.job_operation)


@dp.callback_query_handler(lambda c: c.data == 'new_job', state=Admin.job_operation)
async def new_job(callback: types.CallbackQuery, state: FSMContext):
    """Добавление новых маршрутов"""
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

    await message.reply('Введите идентификатор маршрута:')
    await state.set_state(Job.text)


@dp.message_handler(state=Job.text)
async def save_job(message: types.Message, state: FSMContext):
    """Идентификатор для задания и сохранение в базу данных"""
    async with state.proxy() as data:
        data['text'] = message.text
        current_city = data.get('current_city')

    if not base.get_job(current_city, data['text']):
        base.new_job(current_city, data['image'], data['text'], status=1)
        await bot.send_message(message.from_user.id, f'Маршрут добавлен',
                               reply_markup=job_add)
    else:
        await bot.send_message(message.from_user.id,
                               f'Маршрут с id: {data["text"]} уже добавлен',
                               reply_markup=job_add)
    await state.set_state(Admin.job_operation)


async def check_state_timeout(state: FSMContext, city: str, job_id: str, update, params):
    # # Начинаем отсчет времени
    end_time = time.time() + 18000

    city = city
    job_id = job_id

    while time.time() < end_time:
        current_state = await state.get_state()

        if params == 'start':
            if current_state == User.first_report.state:
                # Если перешли в следующий хендлер - выходим из цикла
                await asyncio.sleep(1)
            else:
                return

        elif params == 'confirm':
            if current_state == User.start_working.state:
                # Если перешли в следующий хендлер - выходим из цикла
                await asyncio.sleep(1)
            else:
                return
    else:
        # Если прошло 5 часов и перехода в следующий хендлер не было - меняем статус на 1
        base.update_job_status(city, job_id, status=1)
        await bot.send_message(chat_id=update.from_user.id,
                               text='Прошло 5 часов. Вы не начали работу. Маршрут отозван',
                               reply_markup=back)
        await state.finish()


async def job_timeout(state: FSMContext, city: str, job_id: str, update):
    end_timer = time.time() + 172800

    city = city
    job_id = job_id

    while time.time() < end_timer:
        current_state = await state.get_state()

        if current_state == User.end_job.state or current_state is None:
            return
        await asyncio.sleep(1)
    else:
        base.update_job_status(city, job_id, status=1)
        await bot.send_message(chat_id=update.from_user.id,
                               text='Прошло 48 часов. Маршрут не завершен. Отмена маршрута',
                               reply_markup=back)
        await state.finish()

async def check_subsciber(user_id) -> bool:
    """Проверка участников групп"""
    for group in USERS_GROUP1 + USERS_GROUP2:
        try:
            chat_member = await bot.get_chat_member(chat_id=group, user_id=user_id)
            if chat_member.status == 'member':
                return True
        except aiogram.utils.exceptions.ChatNotFound:
            pass
        except Exception as e:
            logger.error(e)
    return False


async def check_subscriber_group(user_id):
    """Проверка группы подписчика"""
    for group in USERS_GROUP1 + USERS_GROUP2:
        try:
            chat_member = await bot.get_chat_member(chat_id=group, user_id=user_id)
            if chat_member.status == 'member':
                if group in USERS_GROUP1:
                    return "GROUP1"
                elif group in USERS_GROUP2:
                    return "GROUP2"
        except Exception as e:
            logger.error(e)
    logger.error(f'Пользователь {user_id.from_user.full_name} не состоит ни в одной группе')
    return None
