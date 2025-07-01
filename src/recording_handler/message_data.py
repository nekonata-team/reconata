from abc import ABC, abstractmethod
from dataclasses import dataclass
from logging import getLogger

import discord
import discord.types.threads

logger = getLogger(__name__)


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
