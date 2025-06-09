import argparse
import re
from pathlib import Path

import discord

from container import container
from logging_config import load_logging_config
from types_ import MessageContext

load_logging_config()


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


def get_channel_id_from_url(channel_url):
    # channel_url例: https://discord.com/channels/<guild_id>/<channel_id>
    m = re.match(r"https://discord.com/channels/\d+/(\d+)", channel_url)
    if not m:
        raise ValueError(f"不正なDiscordチャンネルURL: {channel_url}")
    return int(m.group(1))


async def send_messages_to_channel(messages, channel_id: int):
    token = container.config.discord_bot_token()
    intents = discord.Intents.default()
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        channel = client.get_channel(channel_id)
        if channel is None:
            print(f"チャンネルID {channel_id} が見つかりません")
            await client.close()
            return
        # TextChannel型にキャスト
        if not isinstance(channel, discord.TextChannel):
            print(f"チャンネルID {channel_id} はTextChannelではありません")
            await client.close()
            return
        context = MessageContext(channel=channel)
        try:
            async for msg in _aiter(messages):
                await msg.effect(context)
        except Exception as e:
            print(f"送信中にエラー: {e}")
        await client.close()

    # イテレータをasyncイテレータに変換
    async def _aiter(it):
        for item in it:
            yield item

    await client.start(token)


async def main():
    args = parse_args()
    mixed_audio_path = args.mixed_audio_path
    context_path = args.context_path

    try:
        channel_id = get_channel_id_from_url(args.channel_url)
    except ValueError as e:
        print(f"チャンネルURLの解析に失敗: {e}")
        return

    if not mixed_audio_path.exists():
        raise FileNotFoundError(
            f"指定された音声ファイルが存在しません: {mixed_audio_path}"
        )
    if not context_path.exists():
        raise FileNotFoundError(
            f"指定されたコンテキストファイルが存在しません: {context_path}"
        )

    audio_handler = container.audio_handler_from_cli()
    messages = audio_handler(mixed_audio_path, context_path)
    await send_messages_to_channel(messages, channel_id)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
