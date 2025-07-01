from logging import getLogger
from typing import cast

import discord

from container import container
from src.recording_handler.message_data import (
    MessageContext,
)
from src.recording_handler.recording_handler import RecordingHandler

from .enums import Mode, PromptKey, ViewType
from .file_sink import FileSink
from .type import (
    AttendeeData,
    Meeting,
)

logger = getLogger(__name__)


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


stop = discord.SlashCommandGroup("stop", "録音を停止します")


@stop.command(description="議事録モードで録音を停止します")
async def minute(
    ctx: discord.ApplicationContext,
    prompt_key=discord.Option(
        str,
        description="使用するプロンプト",
        default=PromptKey.DEFAULT,
        choices=[
            discord.OptionChoice(name="デフォルト", value=PromptKey.DEFAULT),
            discord.OptionChoice(name="Obsidian", value=PromptKey.OBSIDIAN),
        ],
    ),
    view_type=discord.Option(
        str,
        description="付加するView（ボタン）",
        default=ViewType.EDIT,
        choices=[
            discord.OptionChoice(name="編集ボタン", value=ViewType.EDIT),
            discord.OptionChoice(
                name="コミットボタン + 編集ボタン", value=ViewType.COMMIT
            ),
        ],
    ),
):
    await ctx.defer()

    container.config.summarize_prompt_key.override(prompt_key)
    container.config.view_type.override(view_type)
    msg = stop_recording(ctx, Mode.MINUTE)
    await ctx.respond(msg)


@stop.command(description="文字起こしモードで録音を停止します")
async def transcription(ctx: discord.ApplicationContext):
    await ctx.defer()
    msg = stop_recording(ctx, Mode.TRANSCRIPTION)
    await ctx.respond(msg)


@stop.command(description="保存モードで録音を停止します")
async def save(ctx: discord.ApplicationContext):
    await ctx.defer()
    msg = stop_recording(ctx, Mode.SAVE)
    await ctx.respond(msg)


bot.add_application_command(stop)


@bot.command(description="現在のパラメータや利用中のコンポーネント情報を表示します。")
async def parameters(ctx: discord.ApplicationContext):
    await ctx.defer()
    embed = discord.Embed(title="Current Parameters")
    embed.add_field(name="Model Size", value=container.config.model_size())
    embed.add_field(name="Beam Size", value=str(container.config.beam_size()))
    # PATをマスクして表示
    repo_url = container.config.repo_url()
    if repo_url and repo_url.startswith("https://") and "@github.com/" in repo_url:
        import re

        repo_url = re.sub(r"(https://)[^@]+(@github.com/)", r"\1***\2", repo_url)
    embed.add_field(name="GitHub Repo URL", value=repo_url)

    summarizer_class = type(container.summarizer()).__name__
    transcriber_class = type(container.transcriber()).__name__
    embed.add_field(name="Summarizer", value=summarizer_class)
    embed.add_field(name="Transcriber", value=transcriber_class)

    await ctx.respond(embed=embed)


def stop_recording(ctx: discord.ApplicationContext, mode: Mode):
    container.config.mode.override(mode)
    meeting = meetings.get(ctx.guild.id)

    logger.info(
        f"Stopping recording in {ctx.channel.name} for guild {ctx.guild.id} with mode {mode}"
    )

    if meeting is not None:
        meeting.voice_client.stop_recording()
        return "録音を停止しました。"
    else:
        return "録音は開始されていません。"


async def on_finish_recording(sink: FileSink, channel: discord.TextChannel):
    await sink.vc.disconnect()

    audio_handler: RecordingHandler = container.audio_handler()

    meeting = meetings.get(channel.guild.id)

    if meeting is None:
        return

    attendees = {user: AttendeeData(file) for user, file in sink.audio_data.items()}

    context = MessageContext(channel=channel)

    async for data in audio_handler(attendees):
        await data.effect(context)
    # clean up
    del meetings[channel.guild.id]
