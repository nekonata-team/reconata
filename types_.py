from abc import ABC
from dataclasses import dataclass

import discord
import discord.types.threads


@dataclass
class AttendeeData:
    audio: discord.sinks.AudioData


Attendees = dict[int, AttendeeData]


@dataclass
class Meeting:
    voice_client: discord.VoiceClient


class MessageData(ABC): ...


@dataclass(frozen=True)
class SendData(MessageData):
    content: str | None = None
    file: discord.File | None = None
    files: list[discord.File] | None = None
    embed: discord.Embed | None = None
    view: discord.ui.View | None = None


@dataclass(frozen=True)
class AppendEmbedData(MessageData):
    embed: discord.Embed


@dataclass(frozen=True)
class CreateThreadData(MessageData):
    name: str
    auto_archive_duration: discord.types.threads.ThreadArchiveDuration = 1440
    type: discord.ChannelType | None = None


@dataclass(frozen=True)
class SendThreadData(MessageData):
    content: str | None = None
    files: list[discord.File] | None = None
    embed: discord.Embed | None = None
