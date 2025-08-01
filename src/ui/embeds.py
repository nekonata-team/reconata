import discord

from container import container


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
