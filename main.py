import os
from io import BytesIO
from logging import getLogger
from pathlib import Path
from typing import cast

import discord
from dependency_injector import containers, providers
from dotenv import load_dotenv
from post_process.github_push import GitHubPushPostProcess
from summarizer.gemini import GeminiSummarizer
from summarizer.prompt_provider.formatted_markdown import (
    FormattedMarkdownSummarizePromptProvider,
)
from transcriber.faster_whisper import FasterWhisperTranscriber

from handler import MinuteAudioHandler
from types_ import (
    AppendEmbedData,
    AttendeeData,
    CreateThreadData,
    Meeting,
    SendData,
    SendThreadData,
)
from view import CommitView

load_dotenv()

logger = getLogger(__name__)

bot = discord.Bot()


class Container(containers.DeclarativeContainer):
    config = providers.Configuration()

    prompt_provider = providers.Singleton(FormattedMarkdownSummarizePromptProvider)
    transcriber = providers.Singleton(FasterWhisperTranscriber, model_size="turbo")
    summarizer = providers.Singleton(
        GeminiSummarizer,
        api_key=config.api_key,
        summarize_prompt_provider=prompt_provider,
    )
    post_process = providers.Singleton(
        GitHubPushPostProcess,
        repo_url=config.repo_url,
    )
    audio_handler = providers.Singleton(
        MinuteAudioHandler,
        folder_path=Path("./data"),
        transcriber=transcriber,
        summarizer=summarizer,
        summarize_prompt_provider=prompt_provider,
        post_process=post_process,
    )


container = Container()
container.config.repo_url.from_env("GITHUB_REPO_URL", required=True)
container.config.api_key.from_env("GOOGLE_API_KEY", required=True)
audio_handler = container.audio_handler()

meetings: dict[int, Meeting] = {}


@bot.command()
async def start(ctx: discord.ApplicationContext):
    member = cast(discord.Member, ctx.author)
    voice = member.voice

    if voice is None:
        await ctx.respond("ボイスチャンネルに参加してください。")
        return

    voice = cast(discord.VoiceState, voice)

    if (channel := voice.channel) is not None:
        vc = await channel.connect()
        meetings[ctx.guild.id] = Meeting(voice_client=vc)

        vc.start_recording(
            discord.sinks.MP3Sink(),
            on_finish_recording,
            ctx.channel,
            sync_start=True,
        )
        await ctx.respond("録音を開始しました。")


@bot.command()
async def stop(ctx: discord.ApplicationContext):
    meeting = meetings.get(ctx.guild.id)
    if meeting is not None:
        meeting.voice_client.stop_recording()
        await ctx.delete()
    else:
        await ctx.respond("録音は開始されていません。")


@bot.command()
async def test(ctx: discord.ApplicationContext):
    channel = cast(discord.TextChannel, ctx.channel)

    # メモリ上でファイルを作成

    file_content = "これはテストファイルの内容です。"
    file_obj = BytesIO(file_content.encode("utf-8"))
    file_obj.seek(0)

    data = SendData(
        content="これはテストメッセージです。",
        embed=discord.Embed(
            title="テストメッセージ",
            description="これはテストメッセージです。",
        ),
        view=CommitView(container.post_process()),
        files=[
            discord.File(
                file_obj,
                filename="test.txt",
            )
        ],
    )
    await channel.send(**data.__dict__)
    await ctx.respond("テストメッセージを送信しました。")


async def on_finish_recording(
    sink: discord.sinks.MP3Sink, channel: discord.TextChannel
):
    await sink.vc.disconnect()

    if hasattr(audio_handler, "encoding"):
        audio_handler.encoding = sink.encoding

    meeting = meetings.get(channel.guild.id)

    if meeting is None:
        return

    attendees = {
        user_id: AttendeeData(audio=audio) for user_id, audio in sink.audio_data.items()
    }

    thread: discord.Thread | None = None
    focusing_message: discord.Message | None = None
    for data in audio_handler(attendees):
        if isinstance(data, SendData):
            focusing_message = await channel.send(**data.__dict__)
        elif isinstance(data, AppendEmbedData):
            if (msg := focusing_message) is not None:
                focusing_message = await msg.edit(embeds=[*msg.embeds, data.embed])
            else:
                logger.error("No focusing message to append embed data.")
        elif isinstance(data, CreateThreadData):
            thread = await channel.create_thread(**data.__dict__)
        elif isinstance(data, SendThreadData):
            if thread is not None:
                focusing_message = await thread.send(**data.__dict__)
            else:
                logger.error("No thread to send data to.")

    # clean up
    del meetings[channel.guild.id]


if (token := os.getenv("DISCORD_BOT_TOKEN")) is not None:
    logger.info("Starting Discord bot...")
    bot.run(token)
