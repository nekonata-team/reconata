import asyncio
import time
from dataclasses import dataclass, field

import discord

from src.bot.file_sink import FileSink
from src.recording_handler.recording_handler import RecordingHandler


@dataclass
class Meeting:
    voice_client: discord.VoiceClient
    sink: FileSink
    started_at: float = field(default_factory=time.monotonic)
    recording_handler: RecordingHandler | None = None
    text_channel: discord.TextChannel | None = None
    monitor_task: asyncio.Task | None = None
    monitor_message: discord.Message | None = None
