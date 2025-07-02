import asyncio

import discord
import typer

from container import container
from src.cli.utils import parse_message_url


def handle_embed_command(message_url: str) -> None:
    try:
        _, channel_id, message_id = parse_message_url(message_url)
    except ValueError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(1)

    asyncio.run(
        _print_embed_description(
            container.config.discord_bot_token(),
            channel_id,
            message_id,
        )
    )


async def _print_embed_description(
    token: str, channel_id: int, message_id: int
) -> None:
    intents = discord.Intents.default()
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        try:
            channel = await client.fetch_channel(channel_id)
            if isinstance(channel, discord.TextChannel):
                message = await channel.fetch_message(message_id)
                if message.embeds:
                    for embed in message.embeds:
                        print(embed.description)
                else:
                    print("メッセージにembedがありません")
            else:
                print("TextChannel以外のチャンネルです")
        except Exception as e:
            print(f"取得中にエラー: {e}")
        await client.close()

    await client.start(token)
