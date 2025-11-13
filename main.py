"""Entry point of the bot application."""

import asyncio
import logging
import os

from aiogram import Bot, Dispatcher, F, Router, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ChatType, ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.token import TokenValidationError

# Конфигурация
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is required")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s:%(name)s - %(message)s",
)
logger = logging.getLogger(__name__)

async def main() -> None:
    """Start the bot application."""
    try:
        bot = Bot(
            token=BOT_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
        logger.info("Successfully created bot instance.")
    except TokenValidationError:
        logger.exception("Invalid token provided")
        raise

    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Базовый роутер с фильтрами
    router = Router()
    router.message.filter(lambda msg: msg.chat.type == ChatType.PRIVATE)
    router.callback_query.filter(lambda cb: cb.message.chat.type == ChatType.PRIVATE)
    
    # Импортируем хендлеры
    from handlers import setup_handlers
    setup_handlers(router)
    
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    logger.info("Starting application...")
    asyncio.run(main())