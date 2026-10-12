import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from config import BOT_TOKEN
from database.db import init_db
from middlewares import BanMiddleware
from handlers import (
    common,
    trainer,
    voice_exam,
    exam,
    knowledge_base,
    cheatsheet,
    admin
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("MarieLaveauBot")

async def main():
    if not BOT_TOKEN or BOT_TOKEN == 'YOUR_BOT_TOKEN_HERE':
        logger.error(
            "\n" + "="*60 + "\n"
            "⚠️ ВНИМАНИЕ: BOT_TOKEN НЕ УСТАНОВЛЕН!\n\n"
            "Пожалуйста, добавьте токен вашего Telegram-бота в файл .env:\n"
            "BOT_TOKEN=123456789:ABCdefGHI...\n\n"
            "Получить токен можно бесплатно у @BotFather в Telegram.\n"
            "="*60 + "\n"
        )
        sys.exit(1)

    logger.info("Инициализация базы данных...")
    await init_db()

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()

    # Register BanMiddleware to block banned users across all handlers
    ban_middleware = BanMiddleware()
    dp.message.outer_middleware(ban_middleware)
    dp.callback_query.outer_middleware(ban_middleware)

    # Register routers in priority order
    dp.include_router(common.router)
    dp.include_router(trainer.router)
    dp.include_router(voice_exam.router)
    dp.include_router(exam.router)
    dp.include_router(knowledge_base.router)
    dp.include_router(cheatsheet.router)
    dp.include_router(admin.router)

    logger.info("Marie Laveau Staff Bot успешно запущен!")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен.")
