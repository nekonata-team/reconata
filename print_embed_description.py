import argparse
import asyncio
import re

import discord


def parse_args():
    parser = argparse.ArgumentParser(
        description="Discordメッセージのembed descriptionを表示するCLI"
    )
    parser.add_argument(
        "message_url",
        type=str,
        help="取得したいDiscordメッセージのURL (例: https://discord.com/channels/<guild_id>/<channel_id>/<message_id>)",
    )
    return parser.parse_args()


def parse_message_url(url):
    m = re.match(r"https://discord.com/channels/(\d+)/(\d+)/(\d+)", url)
    if not m:
        raise ValueError(f"不正なDiscordメッセージURL: {url}")
    guild_id, channel_id, message_id = map(int, m.groups())
    return guild_id, channel_id, message_id


async def print_embed_description(token, guild_id, channel_id, message_id):
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


def main():
    from container import container

    args = parse_args()
    try:
        guild_id, channel_id, message_id = parse_message_url(args.message_url)
    except ValueError as e:
        print(e)
        return
    asyncio.run(
        print_embed_description(
            container.config.discord_bot_token(),
            guild_id,
            channel_id,
            message_id,
        )
    )


if __name__ == "__main__":
    main()
