import asyncio
from dataclasses import dataclass

import discord

from src.bot.file_sink import FileSink
from src.recording_handler.recording_handler import RecordingHandler


@dataclass
class Meeting:
    voice_client: discord.VoiceClient
    recording_handler: RecordingHandler | None = None
    text_channel: discord.TextChannel | None = None  # used for logging or notifications
    sink: FileSink | None = None
    started_at: float | None = None
    monitor_task: asyncio.Task | None = None
    monitor_message: discord.Message | None = None
    monitor_interval: int = 20
