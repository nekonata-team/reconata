import logging

from command import configure
from container import container
from logging_config import load_logging_config

load_logging_config()

logger = logging.getLogger(__name__)

bot = configure()

logger.info("Starting Discord bot...")
bot.run(container.config.discord_bot_token())
