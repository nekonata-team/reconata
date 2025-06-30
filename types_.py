import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum
from logging import getLogger
from pathlib import Path

import discord
import discord.types.threads

logger = getLogger(__name__)


class Mode(StrEnum):
    """録音モード"""

    MINUTE = "minute"
    TRANSCRIPTION = "transcription"
    SAVE = "save"


class PromptKey(StrEnum):
    """プロンプトキー"""

    DEFAULT = "default"
    OBSIDIAN = "obsidian"


@dataclass
class AttendeeData:
    raw_file: str

    def format(self, output_path: Path):
        output_path.parent.mkdir(parents=True, exist_ok=True)
        command = [
            "ffmpeg",
            "-f",
            "s16le",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-i",
            self.raw_file,
            str(output_path),
        ]
        try:
            subprocess.run(command, check=True, capture_output=True, text=True)
        except FileNotFoundError:
            logger.error("FFmpeg is not installed or not found in PATH.")
            raise
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to convert: {e}")
            raise


Attendees = dict[int, AttendeeData]


@dataclass
class Meeting:
    voice_client: discord.VoiceClient


@dataclass
class MessageContext:
    channel: discord.TextChannel
    thread: discord.Thread | None = None
    focusing_message: discord.Message | None = None


class MessageData(ABC):
    @abstractmethod
    async def effect(self, context: MessageContext): ...


@dataclass(frozen=True)
class SendData(MessageData):
    content: str | None = None
    files: list[discord.File] | None = None
    embed: discord.Embed | None = None
    view: discord.ui.View | None = None

    async def effect(self, context: MessageContext):
        context.focusing_message = await context.channel.send(**self.__dict__)


@dataclass(frozen=True)
class AppendEmbedData(MessageData):
    embed: discord.Embed

    async def effect(self, context: MessageContext):
        if (msg := context.focusing_message) is not None:
            context.focusing_message = await msg.edit(embeds=[*msg.embeds, self.embed])
        else:
            logger.error("No focusing message to append embed data.")


@dataclass(frozen=True)
class EditMessageData(MessageData):
    content: str | None = None
    embed: discord.Embed | None = None

    async def effect(self, context: MessageContext):
        if (msg := context.focusing_message) is not None:
            context.focusing_message = await msg.edit(**self.__dict__)
        else:
            logger.error("No focusing message to edit with data.")


@dataclass(frozen=True)
class CreateThreadData(MessageData):
    name: str
    auto_archive_duration: discord.types.threads.ThreadArchiveDuration = 1440
    type: discord.ChannelType | None = None

    async def effect(self, context: MessageContext):
        context.thread = await context.channel.create_thread(**self.__dict__)


@dataclass(frozen=True)
class SendThreadData(MessageData):
    content: str | None = None
    files: list[discord.File] | None = None
    embed: discord.Embed | None = None

    async def effect(self, context: MessageContext):
        if (thread := context.thread) is not None:
            context.focusing_message = await thread.send(**self.__dict__)

        else:
            logger.error("No thread to send data to.")
