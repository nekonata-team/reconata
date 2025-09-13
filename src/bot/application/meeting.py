import asyncio
from logging import getLogger

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
from src.ui.embeds import create_recording_monitor_embed
from src.ui.view_builder import CommitViewBuilder, EditViewBuilder

from ..domain.meeting import Meeting
from ..enums import Mode, PromptKey
from ..file_sink import FileSink

logger = getLogger(__name__)


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
        sink = FileSink(loop=asyncio.get_running_loop())
        meeting = Meeting(voice_client=vc, sink=sink)
        self.meetings[guild_id] = meeting
        logger.info(f"Starting recording in {voice_channel.name} for guild {guild_id}")
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
        self,
        guild_id: int,
        channel: discord.TextChannel,
    ):
        meeting = self.meetings.get(guild_id)
        if meeting is None:
            return
        msg = await channel.send(
            embed=discord.Embed(title="録音モニター", description="準備中...")
        )
        meeting.monitor_message = msg

        async def _loop():
            while True:
                await asyncio.sleep(10)
                if (meeting := self.meetings.get(guild_id)) is not None:
                    await msg.edit(
                        embed=create_recording_monitor_embed(meeting.sink.metrics())
                    )

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
        if (
            final
            and message is not None
            and (meeting := self.meetings.get(guild_id)) is not None
        ):
            await message.edit(
                embed=create_recording_monitor_embed(meeting.sink.metrics())
            )


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
