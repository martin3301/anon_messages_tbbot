import asyncio
import logging

from app.middlewares import CheckSubscriptionMiddleware
from config import TOKEN, mainChannel
from aiogram import Bot, Dispatcher
from app.handlers import router
from db.main import init_db

bot = Bot(token=TOKEN)
dp = Dispatcher()


async def main():
    await init_db()
    dp.include_router(router)

    dp.message.middleware(CheckSubscriptionMiddleware(bot, mainChannel))
    dp.callback_query.middleware(CheckSubscriptionMiddleware(bot, mainChannel))

    await dp.start_polling(bot)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Exit")
