import logging

from container import container
from logging_config import load_logging_config
from src.bot.bot import bot

load_logging_config(container.config.log_level())

logger = logging.getLogger(__name__)

logger.info("Starting Discord bot...")
bot.run(container.config.discord_bot_token())
