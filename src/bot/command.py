import asyncio
from datetime import datetime, timedelta
from logging import getLogger
from typing import cast
from zoneinfo import ZoneInfo

import discord
from discord.ext import tasks

from container import container

from .application.meeting import (
    MeetingAlreadyExistsError,
    MeetingNotFoundError,
    MeetingService,
)
from .enums import Mode

TZ = ZoneInfo("Asia/Tokyo")

logger = getLogger(__name__)

bot = discord.Bot()

meeting_service = MeetingService()


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
        try:
            await meeting_service.start_meeting(channel)  # type: ignore
        except MeetingAlreadyExistsError:
            await ctx.respond("すでに録音が開始されています。")
            return
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
    mode_ = cast(Mode, mode)
    try:
        meeting_service.stop_meeting(guild_id, mode_, ctx.channel)
    except MeetingNotFoundError:
        await ctx.respond("録音が開始されていません。")
        return
    await ctx.respond("録音を停止しました。")


@bot.command(description="現在のパラメータや利用中のコンポーネント情報を表示します。")
async def parameters(ctx: discord.ApplicationContext):
    await ctx.defer()

    from src.ui.embeds import create_parameters_embed
    from src.ui.view.edit_parameters import EditParametersView

    embed = create_parameters_embed(ctx.guild.id)
    view = EditParametersView(ctx.guild.id)
    await ctx.respond(embed=embed, view=view)


@tasks.loop(minutes=1)
async def check_schedules():
    """定期的にスケジュールをチェックし、必要であればミーティングを開始します。"""
    logger.info("Checking schedules...")
    for guild in bot.guilds:
        parameters = container.parameters_repository().get_parameters(guild.id)
        schedules = parameters.schedules

        now = datetime.now().astimezone(TZ)
        for schedule in schedules:
            if schedule.schedule.should_run(now):
                try:
                    channel = guild.get_channel(schedule.channel_id)
                    if channel is None or not isinstance(channel, discord.VoiceChannel):
                        logger.warning(
                            "Channel %s not found or not a voice channel in guild %s",
                            schedule.channel_id,
                            guild.id,
                        )
                        continue
                    await meeting_service.start_meeting(channel)
                except MeetingAlreadyExistsError:
                    logger.info(
                        "Meeting already exists for channel %s in guild %s",
                        schedule.channel_id,
                        guild.id,
                    )
                except Exception as e:
                    logger.error(
                        "Error starting meeting for channel %s in guild %s: %s",
                        schedule.channel_id,
                        guild.id,
                        e,
                    )
    logger.info("Finished checking schedules.")


@bot.event
async def on_ready():
    logger.info(f"Logged in as {bot.user}")
    now = datetime.now().astimezone(TZ)
    delay = (
        timedelta(minutes=1)
        - timedelta(seconds=now.second, microseconds=now.microsecond)
    ).total_seconds()

    logger.info(f"Scheduling check_schedules to start in {delay} seconds.")
    await asyncio.sleep(delay)
    check_schedules.start()
