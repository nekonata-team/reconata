from logging import getLogger
from typing import cast

import discord

from .application.meeting import (
    MeetingAlreadyExistsError,
    MeetingNotFoundError,
    MeetingService,
)
from .enums import Mode

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
        meeting_service.stop_meeting(guild_id, mode_)
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
