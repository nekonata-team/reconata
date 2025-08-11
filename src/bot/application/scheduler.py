import asyncio
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import discord
from discord.ext import tasks

from container import container

from .meeting import MeetingAlreadyExistsError, MeetingService

logger = logging.getLogger(__name__)


class SchedulerService:
    def __init__(self, bot: discord.Bot, meeting_service: MeetingService):
        self.bot = bot
        self.meeting_service = meeting_service
        self.parameters_repository = container.parameters_repository()
        self.TZ = ZoneInfo("Asia/Tokyo")

    async def start(self):
        now = datetime.now().astimezone(self.TZ)
        delay = (
            timedelta(minutes=1)
            - timedelta(seconds=now.second, microseconds=now.microsecond)
        ).total_seconds()

        logger.info(f"SchedulerService will start in {delay} seconds")

        await asyncio.sleep(delay)
        self._run.start()

        logger.info("SchedulerService started")

    @tasks.loop(minutes=1)
    async def _run(self):
        now = datetime.now().astimezone(self.TZ)

        logger.debug(f"Checking schedules for {now.strftime('%Y-%m-%d %H:%M:%S')}...")

        for guild in self.bot.guilds:
            parameters = self.parameters_repository.get_parameters(guild.id)

            for schedule in parameters.schedules:
                if schedule.schedule.should_run(now):
                    await self._handle_schedule(guild, schedule.channel_id)

        logger.debug("Finished checking schedules.")

    async def _handle_schedule(self, guild: discord.Guild, channel_id: int):
        channel = guild.get_channel(channel_id)
        if not isinstance(channel, discord.VoiceChannel):
            logger.warning(
                f"Channel {channel_id} not found or not a voice channel in guild {guild.id}"
            )
            return
        try:
            if len(channel.members) > 0:
                await self.meeting_service.start_meeting(channel)
            else:
                logger.info(
                    f"No members in channel {channel_id} in guild {guild.id}, skipping meeting start"
                )
        except MeetingAlreadyExistsError:
            logger.info(
                f"Meeting already exists for channel {channel_id} in guild {guild.id}"
            )
        except Exception as e:
            logger.error(
                f"Error starting meeting for channel {channel_id} in guild {guild.id}: {e}"
            )
