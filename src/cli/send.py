from pathlib import Path

import discord
import typer

from container import container
from src.bot.application.meeting import create_recording_handler
from src.bot.command import bot
from src.bot.enums import Mode
from src.recording_handler.common import create_path_builder
from src.recording_handler.message_data import MessageContext, SendData
from src.recording_handler.minute import MinuteRecordingHandler

from .utils import parse_discord_channel_url


def handle_send_command(
    mixed_audio_path: Path,
    context_path: Path,
    channel_url: str,
) -> None:
    from logging_config import load_logging_config

    load_logging_config(container.config.log_level())

    try:
        guild_id, channel_id = parse_discord_channel_url(channel_url)
    except ValueError as e:
        typer.echo(f"チャンネルURLの解析に失敗: {e}", err=True)
        raise typer.Exit(1)

    _send_messages_to_channel(
        bot,
        guild_id,
        channel_id,
        mixed_audio_path,
        context_path,
    )
    bot.run(container.config.discord_bot_token())


def _send_messages_to_channel(
    bot: discord.Bot,
    guild_id: int,
    channel_id: int,
    mixed_audio_path: Path,
    context_path: Path,
) -> None:
    container.config.mode.override(Mode.MINUTE)

    context = context_path.read_text(encoding="utf-8")

    recording_handler = create_recording_handler(guild_id, Mode.MINUTE)
    path_builder = create_path_builder(Path("./data"))

    if isinstance(recording_handler, MinuteRecordingHandler):
        messages = recording_handler.handle_mixed_audio(
            path_builder, mixed_audio_path, context
        )

        @bot.event
        async def on_ready():
            channel = bot.get_channel(channel_id)
            if channel is None:
                print(f"チャンネルID {channel_id} が見つかりません")
                await bot.close()
                return
            if not isinstance(channel, discord.TextChannel):
                print(f"チャンネルID {channel_id} はTextChannelではありません")
                await bot.close()
                return
            context = MessageContext(channel=channel)
            try:
                last_message = None
                async for last_message in messages:
                    pass

                if isinstance(last_message, SendData):
                    await last_message.effect(context)
                else:
                    print(
                        "最後のメッセージがSendDataではありません。処理をスキップします。"
                    )
            except Exception as e:
                print(f"送信中にエラー: {e}")
