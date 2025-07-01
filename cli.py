import argparse
import re
from pathlib import Path

import discord

from container import container
from src.bot.command import bot, create_recording_handler
from src.bot.enums import Mode
from src.recording_handler.common import create_path_builder
from src.recording_handler.message_data import MessageContext, SendData


def parse_args():
    parser = argparse.ArgumentParser(
        description="Discordチャンネルに音声メッセージを送信するスクリプト"
    )
    parser.add_argument(
        "mixed_audio_path",
        type=Path,
        help="ミックスされた音声ファイルのパス (例: ./mixed.mp3)",
    )
    parser.add_argument(
        "context_path",
        type=Path,
        help="コンテキスト情報が含まれるJSONファイルのパス (例: ./context.json)",
    )
    parser.add_argument(
        "channel_url",
        type=str,
        help="メッセージを送信するDiscordチャンネルのURL",
    )
    return parser.parse_args()


def parse_discord_channel_url(channel_url):
    # channel_url例: https://discord.com/channels/<guild_id>/<channel_id>
    m = re.match(r"https://discord.com/channels/(\d+)/(\d+)", channel_url)
    if not m:
        raise ValueError(f"不正なDiscordチャンネルURL: {channel_url}")
    return int(m.group(1)), int(m.group(2))


def on_ready_send_messages_to_channel(
    bot: discord.Bot,
    guild_id: int,
    channel_id: int,
    mixed_audio_path: Path,
    context_path: Path,
):
    container.mode.override(Mode.MINUTE)

    context = context_path.read_text(encoding="utf-8")

    recording_handler = create_recording_handler(guild_id, Mode.MINUTE)
    path_builder = create_path_builder(Path("./data"))
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
        # TextChannel型にキャスト
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


if __name__ == "__main__":
    from logging_config import load_logging_config

    load_logging_config(container.config.log_level())

    args = parse_args()
    mixed_audio_path = args.mixed_audio_path
    context_path = args.context_path

    try:
        guild_id, channel_id = parse_discord_channel_url(args.channel_url)
    except ValueError as e:
        raise ValueError(f"チャンネルURLの解析に失敗: {e}")

    if not mixed_audio_path.exists():
        raise FileNotFoundError(
            f"指定された音声ファイルが存在しません: {mixed_audio_path}"
        )
    if not context_path.exists():
        raise FileNotFoundError(
            f"指定されたコンテキストファイルが存在しません: {context_path}"
        )

    on_ready_send_messages_to_channel(
        bot,
        guild_id,
        channel_id,
        mixed_audio_path,
        context_path,
    )
    bot.run(container.config.discord_bot_token())
