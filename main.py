from aiogram import Bot, types
from config import TOKEN, SERVER_URL
from aiohttp import web
from bot import bot, dp


Bot.set_current(bot)
app = web.Application()

webhook_path = f'/{TOKEN}'

async def set_webhook():
    webhook_uri = f'{SERVER_URL}{webhook_path}'
    await bot.set_webhook(webhook_uri)
async def on_startup(_):
    await set_webhook()

async def handle_webhook(request):
    url = str(request.url)
    index = url.rfind('/')
    token = url[index+1:]
    if token == TOKEN:
        json_data = await request.json()
        update = types.Update(**json_data)

        await dp.process_update(update)
        return web.Response()
    return web.Response(status=403)

app.router.add_post(f'/{TOKEN}', handle_webhook)


if __name__ == '__main__':
    app.on_startup.append(on_startup)
    web.run_app(
        app,
        host='0.0.0.0',
        port=9090,
    )
