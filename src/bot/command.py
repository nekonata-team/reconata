from dataclasses import dataclass
from logging import getLogger
from typing import cast

import discord

from container import container
from src.post_process.github_push import GitHubPusher
from src.recording_handler.context_provider import ParametersBaseContextProvider
from src.recording_handler.message_data import (
    MessageContext,
)
from src.recording_handler.minute import MinuteRecordingHandler
from src.recording_handler.recording_handler import RecordingHandler
from src.recording_handler.save import SaveToFolderRecordingHandler
from src.recording_handler.transcription import TranscriptionRecordingHandler
from src.summarizer.formatter.mdformat import MdFormatSummaryFormatter
from src.ui.view_builder import CommitViewBuilder, EditViewBuilder

from .attendee import AttendeeData
from .enums import Mode, PromptKey
from .file_sink import FileSink

logger = getLogger(__name__)


@dataclass
class Meeting:
    voice_client: discord.VoiceClient
    recording_handler: RecordingHandler | None = None


bot = discord.Bot()

meetings: dict[int, Meeting] = {}


@bot.command(
    description="録音を開始します。ボイスチャンネルに参加してから実行してください。"
)
async def start(ctx: discord.ApplicationContext):
    await ctx.defer()
    member = cast(discord.Member, ctx.author)
    voice = member.voice

    if voice is None:
        await ctx.respond("ボイスチャンネルに参加してください。")
        return

    voice = cast(discord.VoiceState, voice)

    if (channel := voice.channel) is not None:
        vc = await channel.connect()
        meetings[ctx.guild.id] = Meeting(voice_client=vc)

        logger.info(f"Starting recording in {channel.name} for guild {ctx.guild.id}")

        vc.start_recording(
            FileSink(),
            on_finish_recording,
            ctx.channel,
            sync_start=True,
        )
        await ctx.respond("録音を開始しました。")
    else:
        await ctx.respond("チャンネルが見つかりません。")


@bot.command(description="録音を停止します")
async def stop(
    ctx: discord.ApplicationContext,
    mode=discord.Option(
        Mode,
        name="モード",
        description="録音の処理モードを設定する事ができます",
        default=Mode.MINUTE,
    ),
):
    await ctx.defer()

    guild_id = ctx.guild.id
    meeting = meetings.get(guild_id)

    if meeting is None:
        await ctx.respond("録音は開始されていません。")
        return

    mode_ = Mode(mode)  # 型エラーの対処
    meeting.recording_handler = create_recording_handler(guild_id, mode_)

    logger.info(
        f"Stopping recording in {ctx.channel.name} for guild {ctx.guild.id} with mode {mode_}"
    )

    meeting.voice_client.stop_recording()
    await ctx.respond("録音を停止しました。")


@bot.command(description="現在のパラメータや利用中のコンポーネント情報を表示します。")
async def parameters(ctx: discord.ApplicationContext):
    await ctx.defer()

    from src.ui.embeds import create_parameters_embed
    from src.ui.view.edit_parameters import EditParametersView

    embed = create_parameters_embed(ctx.guild.id)
    view = EditParametersView(ctx.guild.id)
    await ctx.respond(embed=embed, view=view)


async def on_finish_recording(sink: FileSink, channel: discord.TextChannel):
    await sink.vc.disconnect()

    meeting = meetings.get(channel.guild.id)

    if meeting is None:
        return

    if meeting.recording_handler is None:
        return

    attendees = {user: AttendeeData(file) for user, file in sink.audio_data.items()}

    context = MessageContext(channel=channel)

    async for data in meeting.recording_handler(attendees):
        await data.effect(context)
    # clean up
    del meetings[channel.guild.id]


def create_recording_handler(guild_id: int, mode: Mode) -> RecordingHandler:
    if mode == Mode.SAVE:
        return SaveToFolderRecordingHandler()

    parameters_repository = container.parameters_repository()
    parameters = parameters_repository.get_parameters(guild_id)

    if mode == Mode.TRANSCRIPTION:
        container.config.hotwords.override(parameters.hotwords)

        return TranscriptionRecordingHandler(
            transcriber=container.transcriber(),
        )

    if mode == Mode.MINUTE:
        container.config.hotwords.override(parameters.hotwords)
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
