import psycopg2
from aiogram import Bot, types
from loguru import logger

from config import TOKEN, SERVER_URL
from aiohttp import web
from loader import bot, dp, base


Bot.set_current(bot)
app = web.Application()
webhook_path = f'/{TOKEN}'
base.create_user_table()


async def set_webhook():
    webhook_uri = f'{SERVER_URL}{webhook_path}'
    await bot.set_webhook(webhook_uri)

async def setup_bot_commands():
    bot_commands = [
        types.BotCommand("start", "Старт"),
        types.BotCommand("help", "Подсказки"),
        types.BotCommand("config", "Настройки"),
    ]
    await bot.set_my_commands(bot_commands)

async def on_startup(_):
    await set_webhook()
    await setup_bot_commands()

async def handle_webhook(request):
    try:
        json_data = await request.json()
        update = types.Update(**json_data)
        await dp.process_update(update)
        return web.Response()
    except psycopg2.Error as e:
        base.rollback()
        logger.error(e)
        return web.Response()
    except Exception as e:
        logger.error(e)
        return web.Response()


app.router.add_post(f'/{TOKEN}', handle_webhook)


if __name__ == '__main__':
    app.on_startup.append(on_startup)
    web.run_app(
        app,
        host='0.0.0.0',
        port=9090,
    )
