import asyncio
import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from loguru import logger

dp = Dispatcher()
bot = Bot(token=os.getenv('TELEGRAM_BOT_TOKEN'), default=DefaultBotProperties(parse_mode='HTML'))


async def startup():
    bot_info = await bot.me()
    logger.info(f"{bot_info.first_name}, {bot_info.username}, https://t.me/{bot_info.username}")
    await bot.send_message(os.getenv('TELEGRAM_CHAT_ID'), 'bot stated')


async def send_message(message: str, reply_markup=None):
    await bot.send_message(os.getenv('TELEGRAM_CHAT_ID'), message, reply_markup=reply_markup)


async def main():
    asyncio.create_task(startup())  # noqa no awaiting
    # dp.include_router(main_commands.router)

    await dp.start_polling(bot, skip_updates=True)


if __name__ == '__main__':
    asyncio.run(main())
