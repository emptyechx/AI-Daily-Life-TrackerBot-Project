import asyncio
import logging
import sys

from logging.handlers import RotatingFileHandler

from dotenv import load_dotenv
load_dotenv()

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import get_bot_token

from handlers.commands import router as commands_router
from handlers.registration import router as reg_router
from handlers.morning_checkin import router as morning_router
from handlers.day_checkin import router as day_router
from handlers.evening_checkin import router as evening_router
from handlers.notification import router as notif_router
from handlers.edit_profile import router as edit_router

from scheduler import start_scheduler
from ai.gemini_client import configure_gemini

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        RotatingFileHandler('bot.log', maxBytes=10 * 1024 * 1024, backupCount=5, encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)


# ============================================================================
# BOT SETUP
# ============================================================================

def create_bot() -> Bot:
    """Create and return an aiogram `Bot` instance with default properties set."""
    return Bot(
        token= get_bot_token(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

def setup_dispatcher() -> Dispatcher:
    """Create a Dispatcher and include all handler routers."""
    dp = Dispatcher()

    dp.include_router(commands_router)
    dp.include_router(reg_router)
    dp.include_router(notif_router)
    dp.include_router(edit_router)
    dp.include_router(morning_router)
    dp.include_router(day_router)
    dp.include_router(evening_router)

    return dp

# ============================================================================
# STARTUP & SHUTDOWN HANDLERS
# ============================================================================
async def on_startup(bot: Bot):
    """Initializes bot startup, logs progress, and starts the scheduler."""
    logger.info("Bot is starting up...")

    try:
        await start_scheduler(bot)
        logger.info("Scheduler started successfully")
    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}", exc_info=True)
    try:
        configure_gemini()
        logger.info("✅ Gemini AI initialized")
    except Exception as e:
        logger.error(f"❌ Gemini initialization failed: {e}")

    logger.info("Bot startup complete")


async def on_shutdown(bot: Bot):
    """Closes bot session and logs the shutdown process safely."""
    logger.info("Bot is shutting down...")

    try:
        session = getattr(bot, "session", None)
        if session is not None:
            await session.close()
            logger.info("Bot session closed")
    except Exception:
        logger.exception("Error during shutdown")


# ============================================================================
# MAIN FUNCTION
# ============================================================================

async def main():
    """Starts the bot, registers handlers, and manages execution lifecycle."""
    logger.info("Initializing bot...")

    bot = create_bot()
    dp = setup_dispatcher()

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    try:
        logger.info("Starting polling...")
        await dp.start_polling(bot, drop_pending_updates=True)
    except Exception:
        logger.critical("Critical error during polling", exc_info=True)
    finally:
        try:
            session = getattr(bot, "session", None)
            if session is not None:
                await session.close()
        except Exception:
            logger.exception("Error closing bot session in main finally")
        logger.info("Bot stopped")


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped by user")
    except Exception:
        logger.critical("Unexpected error in entry point", exc_info=True)
        sys.exit(1)