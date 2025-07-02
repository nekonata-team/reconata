import re
from typing import NamedTuple


class DiscordMessage(NamedTuple):
    guild_id: int
    channel_id: int
    message_id: int


class DiscordChannel(NamedTuple):
    guild_id: int
    channel_id: int


DISCORD_DOMAINS = (
    r"(?:discord\.com|discordapp\.com|ptb\.discord\.com|canary\.discord\.com)"
)
MESSAGE_URL_PATTERN = re.compile(
    rf"https://{DISCORD_DOMAINS}/channels/(\d+)/(\d+)/(\d+)"
)
CHANNEL_URL_PATTERN = re.compile(rf"https://{DISCORD_DOMAINS}/channels/(\d+)/(\d+)")


def parse_message_url(url: str) -> DiscordMessage:
    if match := MESSAGE_URL_PATTERN.match(url):
        guild_id, channel_id, message_id = map(int, match.groups())
        return DiscordMessage(guild_id, channel_id, message_id)
    raise ValueError(f"不正なDiscordメッセージURL: {url}")


def parse_discord_channel_url(channel_url: str) -> DiscordChannel:
    if match := CHANNEL_URL_PATTERN.match(channel_url):
        guild_id, channel_id = map(int, match.groups())
        return DiscordChannel(guild_id, channel_id)
    raise ValueError(f"不正なDiscordチャンネルURL: {channel_url}")
