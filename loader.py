import asyncio
import time

from aiogram.utils.exceptions import ChatNotFound
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
    if await check_ban(message.from_user.id):
        if message.from_user.id in ADMINS or await check_subsciber(message.from_user.id):
            await bot.send_message(message.from_user.id,
                                   text='Привет! Это бот, который поможет получить маршрут для работы!',
                                   reply_markup=start)


@dp.message_handler(commands=['help'])
async def help_cmd(message: types.Message):
    if await check_ban(message.from_user.id):
        if message.from_user.id in ADMINS or await check_subsciber(message.from_user.id):
            await bot.send_message(message.from_user.id,
                                   text='<b>Памятки для работы с ботом:</b>\n\n'
                                        'Для начала работы необходимо в главном меню выбрать свой город <b>кнопка "Выбрать город"</b>\n\n'
                                        'После подтверждения начала работы назначится первый доступный маршрут\n\n'
                                        'После прохождения каждого <b>5 дома</b> в маршруте нужно написать отчет в чате о проделанной работе \n\n'
                                        'Если отменить полученный маршрут, <b>закроется доступ к боту на 6 часов</b>\n\n'
                                        'Незавершенный маршрут будет автоматически отменен через 48 часов'
                                        'После отправки последнего отчета <b>кнопка "Завершить маршрут"</b>',

                                   reply_markup=back_back)


@dp.message_handler(commands=['config'])
async def config(message: types.Message):
    """Меню настроек"""
    if message.from_user.id in ADMINS:
        await bot.send_message(chat_id=message.from_user.id,
                               text='Меню настроек:',
                               reply_markup=config_kb)


@dp.callback_query_handler(lambda c: c.data == 'update_status')
async def update_status(callback: types.CallbackQuery):
    """Обновить статусы"""
    await callback.answer()
    if callback.from_user.id in ADMINS:
        base.update_status_all_user()
        await bot.edit_message_text(chat_id=callback.from_user.id,
                                    message_id=callback.message.message_id,
                                    text='Статусы работников обновлены',
                                    reply_markup=back_back)


@dp.callback_query_handler(lambda c: c.data == 'cities_list')
async def choise_city(callback: types.CallbackQuery):
    """Вывести все города в инлайн кнопках"""
    await callback.answer()
    if await check_ban(callback.from_user.id):
        cities = get_cities_keyboard(base)
        await bot.edit_message_text(chat_id=callback.from_user.id,
                                    message_id=callback.message.message_id,
                                    text='Выберите город:',
                                    reply_markup=cities)


@dp.callback_query_handler(lambda c: c.data.startswith('back'), state='*')
async def cancel_fsm(callback: types.CallbackQuery, state: FSMContext):
    """Выйти из FSM"""
    await callback.answer()
    if await check_ban(callback.from_user.id):
        if callback.data == 'back':
            if await check_ban(callback.from_user.id):
                await bot.edit_message_text(chat_id=callback.from_user.id,
                                            message_id=callback.message.message_id,
                                            text='Привет! Это бот, который поможет получить маршрут для работы!',
                                            reply_markup=start)
            await state.finish()

        elif callback.data == 'back_ban':
            await dp.storage.update_data(chat=callback.from_user.id, data={'key': 'stop'})
            user_data = base.get_user_data(str(callback.from_user.id))
            city = user_data[1]
            job_id = user_data[2]

            base.update_job_status(city, job_id, status=1)
            base.update_user_status(str(callback.from_user.id), status=0)
            await bot.delete_message(chat_id=callback.from_user.id, message_id=callback.message.message_id)
            await bot.send_message(chat_id=callback.from_user.id,
                                   text='Маршрут отменен. Доступ ограничен на 6 часов.\nПо истечению этого времени используйте команду /start')
            await state.finish()

            # ожидание разбана
            asyncio.create_task(ban_timeout(str(callback.from_user.id)))

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
            else:
                logger.info('юзер не состоит ни в одной группе')
                await state.finish()
                return
    else:
        await state.finish()


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
        if not base.get_user_city(str(callback.from_user.id)):
            base.set_user_info(str(callback.from_user.id), city_name, status=1)
        else:
            base.update_user_info(str(callback.from_user.id), city_name, status=1)
        await bot.edit_message_text(chat_id=callback.from_user.id,
                                    message_id=callback.message.message_id,
                                    text=f'Выбран город: {city_name}. Приступить к работе?',
                                    reply_markup=ready_to_work)
        await state.set_state(User.get_job)


@dp.callback_query_handler(lambda c: c.data == 'start_job', state=User.get_job)
async def start_work(callback: types.CallbackQuery, state: FSMContext):
    """Подготовка к работе"""
    await callback.answer()

    await bot.delete_message(chat_id=callback.from_user.id, message_id=callback.message.message_id)

    city = base.get_user_city(str(callback.from_user.id))
    job = base.get_job_photo_id(city[0], status=1)

    if job:
        group = await check_subscriber_group(callback.from_user.id)
        if group == 'GROUP1':
            await bot.send_message(chat_id=GROUP_CHAT_ID[0],
                                   text=f'Работник <a href="tg://user?id={callback.from_user.id}">{callback.from_user.full_name}</a> приступил к работе\n'
                                        f'Город: {city[0]}\n'
                                        f'Назначен участок: # {job[1]}')
        elif group == 'GROUP2':
            await bot.send_message(chat_id=GROUP_CHAT_ID[1],
                                   text=f'Работник <a href="tg://user?id={callback.from_user.id}">{callback.from_user.full_name}</a> приступил к работе\n'
                                        f'Город: {city[0]}\n'
                                        f'Назначен участок: # {job[1]}')
        else:
            logger.info('юзер не состоит ни в одной группе')
            await state.finish()
            return

        base.set_job_id(job[1], str(callback.from_user.id))
        base.update_job_status(city[0], job[1], status=0)

        await bot.send_photo(chat_id=callback.from_user.id,
                             photo=job[0],
                             caption=f'Вам присвоен участок # {job[1]}\n\n'
                                     'Нажмите <b>"Далее"</b>, чтобы начать работу\n\n'
                                     '<b>В СЛУЧАЕ ОТМЕНЫ ДОСТУП К БОТУ БУДЕТ ОГРАНИЧЕН НА 6 ЧАСОВ</b>',
                             reply_markup=to_work_ban)
        await state.set_state(User.start_working)

        # Таймер до завершения маршрута
        asyncio.create_task(check_state_timeout(state, city[0], job[1], callback))

    else:
        await bot.send_message(chat_id=callback.from_user.id,
                               text='На данный момент нет доступных маршрутов, повторите попытку позже',
                               reply_markup=back_back)
        base.update_status(city[0], status=1)
        await state.finish()


@dp.callback_query_handler(lambda c: c.data == 'start_work', state=User.start_working)
async def started_work(callback: types.CallbackQuery, state: FSMContext):
    """Начало работы работника"""
    await callback.answer()
    base.set_message_id(str(callback.from_user.id), callback.message.message_id)

    await bot.send_message(chat_id=callback.from_user.id,
                           text='Можно приступать к работе. Отчеты необходимо присылать в чат. По завершению маршрута, нажмите на "Завершить маршрут"\n',
                           reply_markup=user_send_report
                           )

    await state.set_state(User.make_report)


@dp.callback_query_handler(lambda c: c.data == 'mess_ban', state=User.make_report)
async def message_with_ban(callback: types.CallbackQuery, state: FSMContext):
    """Предупреждение о бане на 6 часов при отмене маршрута"""
    await callback.answer()
    await bot.edit_message_text(chat_id=callback.from_user.id,
                                message_id=callback.message.message_id,
                                text='В случае отмены доступ к боту будет <b>ограничен на 6 часов</b>',
                                reply_markup=mess_ban)
    await state.set_state(User.continue_work)


@dp.callback_query_handler(lambda c: c.data == 'continue_work', state=User.continue_work)
async def continue_work(callback: types.CallbackQuery, state: FSMContext):
    """Продолжаем работу"""
    await callback.answer()
    await bot.edit_message_text(chat_id=callback.from_user.id,
                                message_id=callback.message.message_id,
                                text='Отчеты необходимо присылать в чат. По завершению маршрута, нажмите на "Завершить маршрут"',
                                reply_markup=user_send_report)
    await state.set_state(User.make_report)


@dp.callback_query_handler(lambda c: c.data == 'end_work_job', state=User.make_report)
async def end_work(callback: types.CallbackQuery, state: FSMContext):
    """Завершается маршрут"""
    await callback.answer()

    message = base.get_user_data(str(callback.from_user.id))

    group = await check_subscriber_group(callback.from_user.id)
    if group == 'GROUP1':
        await bot.send_message(chat_id=GROUP_CHAT_ID[0],
                               text=f'Работник <a href="tg://user?id={callback.from_user.id}">{callback.from_user.full_name}</a> завершил маршрут\n'
                                    f'Город: {message[1]}\n'
                                    f'Маршрут: # {message[2]}\n'
                               )
    elif group == 'GROUP2':
        await bot.send_message(chat_id=GROUP_CHAT_ID[1],
                               text=f'Работник <a href="tg://user?id={callback.from_user.id}">{callback.from_user.full_name}</a> завершил маршрут\n'
                                    f'Город: {message[1]}\n'
                                    f'Маршрут: # {message[2]}\n'
                               )
    else:
        logger.info('юзер не состоит ни в одной группе')
        await state.finish()

    await bot.delete_message(chat_id=callback.from_user.id, message_id=message[-1])

    await bot.edit_message_text(chat_id=callback.from_user.id,
                                message_id=callback.message.message_id,
                                text='Маршрут завершен',
                                reply_markup=back_main)
    await state.set_state(User.end_job)


@dp.callback_query_handler(lambda c: c.data == 'new_city')
async def new_city(callback: types.CallbackQuery, state: FSMContext):
    """Добавить новый город"""
    await callback.answer()
    await state.set_state(City.city)

    await bot.edit_message_text(chat_id=callback.from_user.id,
                                message_id=callback.message.message_id,
                                text='Название нового города:',
                                reply_markup=back_cancel)


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
                               reply_markup=back_cancel)
        await state.finish()


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
                                    reply_markup=back_back)
    else:
        await bot.edit_message_text(chat_id=callback.from_user.id,
                                    message_id=callback.message.message_id,
                                    text=f'Ошибка удаления города: {current_city}',
                                    reply_markup=back_back)
    await state.finish()


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

    jobs_kb_list = get_jobs_kb(base, city)
    if jobs_kb_list:
        for jobs_kb in jobs_kb_list:
            await bot.send_message(chat_id=callback.from_user.id,
                                   text='Все маршруты:',
                                   reply_markup=jobs_kb)
        await state.set_state(Admin.jobs_list)
    else:
        await bot.edit_message_text(chat_id=callback.from_user.id,
                                    message_id=callback.message.message_id,
                                    text='Ни одного маршрута не добавлено',
                                    reply_markup=back_back)


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
                           reply_markup=back_cancel)
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


async def check_state_timeout(state: FSMContext, city: str, job_id: str, update):
    # Начинаем отсчет времени
    end_time = time.time() + 172_800

    while time.time() < end_time:
        current_state = await state.get_state()
        data = await dp.storage.get_data(chat=update.from_user.id)
        if current_state is None:
            return
        elif current_state.title().lower() != User.end_job.state.lower():
            await asyncio.sleep(1)
            if data.get('key') == 'stop':
                return
        else:
            return
    else:

        base.update_job_status(city, job_id, status=1)
        await bot.send_message(chat_id=update.from_user.id,
                               text='Прошло 48 часов. Маршрут не завершен. Отмена маршрута',
                               reply_markup=back_main)
        await state.finish()


async def check_subsciber(user_id) -> bool:
    """Проверка участников групп"""
    for group in USERS_GROUP1 + USERS_GROUP2:
        try:
            chat_member = await bot.get_chat_member(chat_id=group, user_id=user_id)
            if chat_member.status == 'member':
                return True
        except ChatNotFound:
            pass
        except Exception as e:
            logger.error(e)
            return False
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
        except ChatNotFound:
            pass
        except Exception as e:
            logger.error(e)
    logger.error(f'Пользователь {user_id.from_user.full_name} не состоит ни в одной группе')
    return None


async def ban_timeout(user_id):
    """Таймер бана"""
    end_timer = time.time() + 21_600
    while time.time() < end_timer:
        await asyncio.sleep(1)
    else:
        base.update_user_status(user_id=user_id, status=1)


async def check_ban(user_id) -> bool:
    """Проверка временного бана"""
    user_data = base.get_user_data(str(user_id))
    if user_data:
        status = user_data[3]
        if status == 1:
            return True
        return False
    return True
