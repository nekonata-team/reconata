import asyncio
import time
from dataclasses import dataclass
from logging import getLogger
from typing import cast

import discord

from container import container
from src.post_process.github_push import GitHubPusher
from src.recording_handler.attendee import AttendeeData
from src.recording_handler.context_provider import ParametersBaseContextProvider
from src.recording_handler.message_data import MessageContext
from src.recording_handler.minute import MinuteRecordingHandler
from src.recording_handler.recording_handler import RecordingHandler
from src.recording_handler.save import SaveToFolderRecordingHandler
from src.recording_handler.transcription import TranscriptionRecordingHandler
from src.summarizer.formatter.mdformat import MdFormatSummaryFormatter
from src.ui.view_builder import CommitViewBuilder, EditViewBuilder

from ..enums import Mode, PromptKey
from ..file_sink import FileSink

logger = getLogger(__name__)


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


class MeetingAlreadyExistsError(Exception):
    pass


class MeetingNotFoundError(Exception):
    pass


class MeetingService:
    def __init__(self):
        self.meetings: dict[int, Meeting] = {}

    async def start_meeting(self, voice_channel: discord.VoiceChannel):
        guild_id = voice_channel.guild.id

        if guild_id in self.meetings:
            raise MeetingAlreadyExistsError(
                f"Meeting already exists for guild {guild_id}"
            )
        vc = await voice_channel.connect()
        meeting = Meeting(voice_client=vc)
        self.meetings[guild_id] = meeting
        logger.info(f"Starting recording in {voice_channel.name} for guild {guild_id}")
        sink = FileSink(loop=asyncio.get_running_loop())
        meeting.sink = sink
        meeting.started_at = time.monotonic()
        vc.start_recording(
            sink,
            self.on_finish_recording,
            guild_id,
            sync_start=True,
        )

    def stop_meeting(
        self,
        guild_id: int,
        mode: Mode,
        text_channel: discord.TextChannel,
    ):
        meeting = self.meetings.get(guild_id)

        if meeting is None:
            raise MeetingNotFoundError(f"No meeting exists for guild {guild_id}")

        meeting.recording_handler = create_recording_handler(guild_id, mode)
        meeting.text_channel = text_channel

        logger.info(f"Stopping recording for guild {guild_id} with mode {mode}")

        meeting.voice_client.stop_recording()  # This will call `on_finish_recording`
        meeting = self.meetings[guild_id]

    async def on_finish_recording(self, sink: FileSink, guild_id: int):
        await sink.close()
        await sink.vc.disconnect()

        meeting = self.meetings.get(guild_id)

        if meeting is None:
            return

        if (handler := meeting.recording_handler) is not None and (
            channel := meeting.text_channel
        ) is not None:
            attendees = {
                user: AttendeeData(file) for user, file in sink.audio_data.items()
            }

            context = MessageContext(channel=channel)

            async for data in handler(attendees):
                await data.effect(context)
        else:
            raise ValueError(
                f"Recording handler or text channel not set for guild {guild_id}"
            )

        try:
            await self._stop_monitoring(guild_id, final=True)
        finally:
            del self.meetings[guild_id]

    async def start_monitoring(
        self, guild_id: int, channel: discord.TextChannel, interval: int = 20
    ):
        meeting = self.meetings.get(guild_id)
        if meeting is None:
            return
        meeting.monitor_interval = max(10, min(60, interval))
        embed = self._build_status_embed(guild_id)
        msg = await channel.send(embed=embed)
        meeting.monitor_message = msg

        async def _loop():
            while True:
                await asyncio.sleep(meeting.monitor_interval)
                m = self.meetings.get(guild_id)
                if m is None:
                    break
                try:
                    await msg.edit(embed=self._build_status_embed(guild_id))
                except Exception:
                    break

        meeting.monitor_task = asyncio.create_task(_loop())

    async def _stop_monitoring(self, guild_id: int, final: bool = False):
        meeting = self.meetings.get(guild_id)
        if meeting is None:
            return
        task = meeting.monitor_task
        message = meeting.monitor_message
        meeting.monitor_task = None
        if task is not None and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        if final and message is not None:
            try:
                await message.edit(embed=self._build_status_embed(guild_id))
            except Exception:
                pass

    def _build_status_embed(self, guild_id: int) -> discord.Embed:
        meeting = self.meetings.get(guild_id)
        title = "🎙️ 録音モニター"
        color = discord.Color.green()
        if meeting is None:
            embed = discord.Embed(title=title, color=discord.Color.red())
            embed.add_field(name="状態", value="未開始")
            return embed
        sink = meeting.sink
        if sink is None:
            embed = discord.Embed(title=title, color=discord.Color.red())
            embed.add_field(name="状態", value="未開始")
            return embed
        metrics = sink.metrics()
        state = "録音中" if not metrics["closed"] else "停止"
        if metrics["closed"]:
            color = discord.Color.orange()
        started = meeting.started_at or time.monotonic()
        dur = max(0, int(time.monotonic() - started))
        last = metrics["last_packet"]
        since = "-" if last == 0 else f"{int(time.monotonic() - last)}s"
        vc_name = "-"
        if meeting.voice_client and meeting.voice_client.channel is not None:
            vc = cast(discord.VoiceChannel, meeting.voice_client.channel)
            vc_name = getattr(vc, "name", "-")
        b = metrics["bytes_total"]
        human = self._human_bytes(b)
        embed = discord.Embed(title=title, color=color)
        embed.add_field(name="状態", value=state)
        embed.add_field(name="経過", value=f"{dur}s")
        embed.add_field(name="VC", value=vc_name, inline=False)
        embed.add_field(name="受信ユーザー", value=str(metrics["files"]))
        embed.add_field(name="データ量", value=human)
        embed.add_field(name="最終受信", value=since)
        embed.add_field(
            name="キュー",
            value=f"{metrics['queue_size']}/{metrics['queue_max']}",
        )
        embed.add_field(name="ライター", value=metrics["writer_state"], inline=False)
        return embed

    def _human_bytes(self, n: int) -> str:
        s = float(n)
        for unit in ["B", "KB", "MB", "GB"]:
            if s < 1024.0:
                return f"{s:.1f}{unit}"
            s /= 1024.0
        return f"{s:.1f}TB"


def create_recording_handler(guild_id: int, mode: Mode) -> RecordingHandler:
    if mode == Mode.SAVE:
        return SaveToFolderRecordingHandler()

    parameters_repository = container.parameters_repository()
    parameters = parameters_repository.get_parameters(guild_id)

    if mode == Mode.TRANSCRIPTION:
        return TranscriptionRecordingHandler(
            transcriber=container.transcriber(),
        )

    if mode == Mode.MINUTE:
        container.config.summarize_prompt_key.override(
            parameters.prompt_key or PromptKey.DEFAULT
        )

        view_builder = (
            CommitViewBuilder(lambda: _pusher_builder(guild_id))
            if parameters.github is not None
            else EditViewBuilder()
        )
        context_provider = ParametersBaseContextProvider(parameters)
        formatter = MdFormatSummaryFormatter()

        return MinuteRecordingHandler(
            transcriber=container.transcriber(),
            summarizer=container.summarizer(),
            summarize_prompt_provider=container.prompt_provider(),
            summary_formatter=formatter,
            view_builder=view_builder,
            context_provider=context_provider,
        )

    return container.audio_handler()


def _pusher_builder(guild_id: int) -> GitHubPusher | None:
    parameters_repository = container.parameters_repository()
    parameters = parameters_repository.get_parameters(guild_id=guild_id)

    data = parameters.github
    if data is None:
        return None
    return GitHubPusher(
        repo_url=data.repo_url,
        local_repo_path=data.local_repo_path,
    )
