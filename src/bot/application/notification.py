import os
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from functools import cached_property

import discord
from torch.cuda import is_available as is_cuda_available

from container import container


class NotificationService(ABC):
    @abstractmethod
    async def send_ready_notification(self):
        pass

    @abstractmethod
    async def send_disconnect_notification(self):
        pass

    @abstractmethod
    async def send_resumed_notification(self):
        pass


class NoopNotificationService(NotificationService):
    async def send_ready_notification(self):
        pass

    async def send_disconnect_notification(self):
        pass

    async def send_resumed_notification(self):
        pass


class DiscordNotificationService(NotificationService):
    def __init__(self, bot: discord.Bot, channel_id: int):
        self.bot = bot
        self.system_channel_id = channel_id
        self._start_time = datetime.now(timezone.utc)

    @property
    def _bot_name(self) -> str:
        if self.bot.user:
            return f"<@{self.bot.user.id}>"
        return "Unknown Bot"

    def _get_common_fields(self) -> list[tuple[str, str]]:
        return [("Guilds", str(len(self.bot.guilds)))]

    async def send_ready_notification(self):
        await self._send(
            f"{self._bot_name} が起動しました。",
            fields=self._get_common_fields()
            + [
                ("CUDA", "Available" if is_cuda_available() else "Not Available"),
                ("Summarizer", container.summarizer().__class__.__name__),
                (
                    "Transcriber",
                    f"{container.transcriber().__class__.__name__} {os.getenv('MODEL_SIZE') or 'default'}",
                ),
            ],
            color=discord.Color.green(),
        )

    async def send_disconnect_notification(self):
        await self._send(
            f"{self._bot_name} が切断されました。再接続を試みています。",
            fields=self._get_common_fields(),
            color=discord.Color.orange(),
        )

    async def send_resumed_notification(self):
        await self._send(
            f"{self._bot_name} が再接続されました。",
            fields=self._get_common_fields(),
            color=discord.Color.blue(),
        )

    @cached_property
    def _channel(self) -> discord.abc.Messageable:
        channel = self.bot.get_channel(self.system_channel_id)
        if isinstance(channel, discord.abc.Messageable):
            return channel
        raise ValueError("Channel is not messageable")

    async def _send(
        self,
        message: str,
        fields: list[tuple[str, str]],
        color: discord.Color,
    ):
        embed = discord.Embed(
            title="reconata: system notification",
            description=message,
            color=color,
            timestamp=datetime.now(timezone.utc),
        )
        for name, value in fields:
            embed.add_field(name=name, value=value)
        await self._channel.send(embed=embed)
