from aiogram import types, Dispatcher, Bot
from config import TOKEN


bot = Bot(TOKEN)
dp = Dispatcher(bot)


@dp.message_handler(commands=['start'])
async def start_command_handler(message: types.Message):
    await message.answer('Привет! Я твой телеграм-бот!')


@dp.message_handler()
async def echo_message_handler(message: types.Message):
    await message.answer(message.text)

