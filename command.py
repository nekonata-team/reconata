from io import BytesIO
from typing import cast

import discord

from container import container
from file_sink import FileSink
from handler.audio_handler import AudioHandler
from types_ import (
    AttendeeData,
    Meeting,
    MessageContext,
    Mode,
    PromptKey,
    SendData,
)
from view import CommitView


def configure() -> discord.Bot:
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
            description="使用するプロンプトキー",
            default=PromptKey.DEFAULT,
            choices=[
                discord.OptionChoice(name="デフォルト", value=PromptKey.DEFAULT),
                discord.OptionChoice(name="Obsidian", value=PromptKey.OBSIDIAN),
            ],
        ),
    ):
        container.config.summarize_prompt_key.override(prompt_key)
        await stop_recording(ctx, Mode.MINUTE)

    @stop.command(description="文字起こしモードで録音を停止します")
    async def transcription(ctx: discord.ApplicationContext):
        await stop_recording(ctx, Mode.TRANSCRIPTION)

    @stop.command(description="保存モードで録音を停止します")
    async def save(ctx: discord.ApplicationContext):
        await stop_recording(ctx, Mode.SAVE)

    bot.add_application_command(stop)

    @bot.command(description="テストメッセージとテストファイルを送信します。")
    async def test(ctx: discord.ApplicationContext):
        await ctx.defer()
        channel = cast(discord.TextChannel, ctx.channel)

        file_content = "これはテストファイルの内容です。"
        file_obj = BytesIO(file_content.encode("utf-8"))
        file_obj.seek(0)

        data = SendData(
            content="これはテストメッセージです。",
            embed=discord.Embed(
                title="テストメッセージ",
                description="これはテストメッセージです。",
            ),
            view=CommitView(container.pusher()),
            files=[
                discord.File(
                    file_obj,
                    filename="test.txt",
                )
            ],
        )
        await channel.send(**data.__dict__)
        await ctx.respond("テストメッセージを送信しました。")

    @bot.command(
        description="現在のパラメータや利用中のコンポーネント情報を表示します。"
    )
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
        embed.add_field(name="Mode", value=container.config.mode())

        await ctx.respond(embed=embed)

    async def stop_recording(ctx: discord.ApplicationContext, mode: Mode):
        """録音停止の共通処理"""
        await ctx.defer()

        container.config.mode.override(mode)
        meeting = meetings.get(ctx.guild.id)
        if meeting is not None:
            meeting.voice_client.stop_recording()
            await ctx.delete()
        else:
            await ctx.respond("録音は開始されていません。")

    async def on_finish_recording(sink: FileSink, channel: discord.TextChannel):
        await sink.vc.disconnect()

        audio_handler: AudioHandler = container.audio_handler()
        audio_handler.encoding = "mp3"

        meeting = meetings.get(channel.guild.id)

        if meeting is None:
            return

        attendees = {user: AttendeeData(file) for user, file in sink.audio_data.items()}

        context = MessageContext(channel=channel)

        async for data in audio_handler(attendees):
            await data.effect(context)
        # clean up
        del meetings[channel.guild.id]

    return bot
