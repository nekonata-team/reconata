import asyncio
from logging import getLogger
from os import getenv
from typing import cast

import discord

from .application.meeting import (
    MeetingAlreadyExistsError,
    MeetingNotFoundError,
    MeetingService,
)
from .application.notification import (
    DiscordNotificationService,
    NoopNotificationService,
)
from .application.scheduler import SchedulerService
from .enums import Mode

logger = getLogger(__name__)

# Bot
bot = discord.Bot()

# Services
meeting_service = MeetingService()
scheduler_service = SchedulerService(bot, meeting_service)
notification_service = (
    DiscordNotificationService(bot, int(channel_id))
    if (channel_id := getenv("SYSTEM_CHANNEL_ID")) is not None and channel_id.isdigit()
    else NoopNotificationService()
)


@bot.command(
    description="録音を開始します。ボイスチャンネルに参加してから実行してください。"
)
async def start(ctx: discord.ApplicationContext):
    await ctx.defer()
    member = cast(discord.Member, ctx.author)
    voice = member.voice

    if voice is None:
        await ctx.followup.send("ボイスチャンネルに参加してください。")
        return

    voice = cast(discord.VoiceState, voice)

    if (channel := voice.channel) is not None:
        # 接続・開始が長引くとインタラクションの期限やGW心拍に影響するためタイムアウトを付与
        timeout_sec = int(getenv("VOICE_CONNECT_TIMEOUT", "20"))
        try:
            await asyncio.wait_for(
                meeting_service.start_meeting(channel),  # type: ignore
                timeout=timeout_sec,
            )
        except MeetingAlreadyExistsError:
            await ctx.followup.send("すでに録音が開始されています。")
            return
        except asyncio.TimeoutError:
            await ctx.followup.send(
                f"ボイス接続がタイムアウトしました（{timeout_sec}s）。もう一度お試しください。"
            )
            return
        except discord.Forbidden:
            await ctx.followup.send("ボイスチャンネルへの接続権限がありません。")
            return
        except discord.HTTPException:
            await ctx.followup.send(
                "Discord API エラーにより接続に失敗しました。少し待って再試行してください。"
            )
            return
        await ctx.followup.send("録音を開始しました。")
        try:
            if isinstance(ctx.channel, discord.TextChannel):
                await meeting_service.start_monitoring(ctx.guild.id, ctx.channel)
        except Exception:
            pass
    else:
        await ctx.followup.send("チャンネルが見つかりません。")


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
        await ctx.followup.send("録音が開始されていません。")
        return
    await ctx.followup.send("録音を停止しました。")


@bot.command(description="現在のパラメータや利用中のコンポーネント情報を表示します。")
async def parameters(ctx: discord.ApplicationContext):
    await ctx.defer()

    from src.ui.embeds import create_parameters_embed
    from src.ui.view.edit_parameters import EditParametersView

    embed = create_parameters_embed(ctx.guild.id)
    view = EditParametersView(ctx.guild.id)
    await ctx.followup.send(embed=embed, view=view)


@bot.event
async def on_ready():
    logger.info(f"Logged in as {bot.user}")
    # await notification_service.send_ready_notification()
    # await scheduler_service.start()


@bot.event
async def on_disconnect():
    await notification_service.send_disconnect_notification()


@bot.event
async def on_resumed():
    await notification_service.send_resumed_notification()
