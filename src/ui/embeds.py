import time
from typing import cast

import discord

from container import container
from src.bot.domain.meeting import Meeting


def create_parameters_embed(guild_id: int) -> discord.Embed:
    """ギルドのパラメータ情報を表示するEmbedを作成する"""
    repository = container.parameters_repository()
    params = repository.get_parameters(guild_id)

    embed = discord.Embed(title="📝 パラメータ設定", color=discord.Color.blue())

    # プロンプトキー
    prompt_key = params.prompt_key.value if params.prompt_key else "default"
    embed.add_field(name="プロンプトキー", value=f"`{prompt_key}`", inline=False)

    # 追加コンテキスト
    if params.additional_context:
        context_preview = (
            params.additional_context[:100] + "..."
            if len(params.additional_context) > 100
            else params.additional_context
        )
        embed.add_field(
            name="追加コンテキスト", value=f"```{context_preview}```", inline=False
        )
    else:
        embed.add_field(name="追加コンテキスト", value="未設定", inline=False)

    # GitHub リポジトリURL
    if (github := params.github) is not None:
        masked_url = github.repo_url
        if "@github.com/" in masked_url:
            import re

            masked_url = re.sub(
                r"(https://)[^@]+(@github.com/)", r"\1***\2", masked_url
            )
        embed.add_field(name="GitHub リポジトリ", value=masked_url, inline=False)
    else:
        embed.add_field(name="GitHub リポジトリ", value="未設定", inline=False)

    # ユーザー名マッピング
    if params.user_names:
        user_count = len(params.user_names)
        embed.add_field(
            name="ユーザー名マッピング", value=f"{user_count}件設定済み", inline=False
        )
    else:
        embed.add_field(name="ユーザー名マッピング", value="未設定", inline=False)

    # スケジュール
    if params.schedules:
        schedule_lines = [
            f"<#{s.channel_id}>: {s.schedule.to_string()}" for s in params.schedules
        ]
        embed.add_field(
            name="スケジュール",
            value="\n".join(schedule_lines) if schedule_lines else "なし",
            inline=False,
        )
    else:
        embed.add_field(name="スケジュール", value="なし", inline=False)

    return embed


def create_recording_monitor_embed(
    meeting: Meeting | None,
) -> discord.Embed:
    title = "🎙️ 録音モニター"
    color = discord.Color.green()
    if meeting is None:
        embed = discord.Embed(title=title, color=discord.Color.red())
        embed.add_field(name="状態", value="未開始")
        return embed
    sink = meeting.sink
    if sink is None:
        embed = discord.Embed(title=title, color=discord.Color.red())
        embed.add_field(name="状態", value="未開始")
        return embed
    metrics = sink.metrics()
    state = "録音中" if not metrics["closed"] else "停止"
    if metrics["closed"]:
        color = discord.Color.orange()
    started = meeting.started_at or time.monotonic()
    dur = max(0, int(time.monotonic() - started))
    last = metrics["last_packet"]
    since = "-" if last == 0 else f"{int(time.monotonic() - last)}s"
    vc_name = "-"
    voice_client = meeting.voice_client
    if voice_client is not None and getattr(voice_client, "channel", None) is not None:
        vc = cast(discord.VoiceChannel, voice_client.channel)
        vc_name = getattr(vc, "name", "-")
    b = metrics["bytes_total"]
    human = _human_bytes(b)
    embed = discord.Embed(title=title, color=color)
    embed.add_field(name="状態", value=state)
    embed.add_field(name="経過", value=f"{dur}s")
    embed.add_field(name="VC", value=vc_name, inline=False)
    embed.add_field(name="受信ユーザー", value=str(metrics["files"]))
    embed.add_field(name="データ量", value=human)
    embed.add_field(name="最終受信", value=since)
    embed.add_field(
        name="キュー", value=f"{metrics['queue_size']}/{metrics['queue_max']}"
    )
    embed.add_field(name="ライター", value=metrics["writer_state"], inline=False)
    return embed


def _human_bytes(n: int) -> str:
    s = float(n)
    for unit in ["B", "KB", "MB", "GB"]:
        if s < 1024.0:
            return f"{s:.1f}{unit}"
        s /= 1024.0
    return f"{s:.1f}TB"
