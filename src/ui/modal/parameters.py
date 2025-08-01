import logging
from typing import Mapping
from urllib.parse import urlparse

import discord

from container import container
from src.bot.enums import PromptKey
from src.parameters_repository.parameters_repository import (
    GitHub,
    MeetingSchedule,
    Parameters,
    parse_schedule_from_string,
)
from src.ui.embeds import create_parameters_embed

logger = logging.getLogger(__name__)


def _extract_repo_name(repo_url: str) -> str:
    path = urlparse(repo_url).path.rstrip("/")
    name = path.split("/")[-1]
    if name.endswith(".git"):
        name = name[: -len(".git")]
    return name


def _parse_prompt_key(raw: str | None) -> tuple[PromptKey | None, str | None]:
    key = (raw or "").strip()
    if not key:
        return None, None
    try:
        return PromptKey(key), None
    except ValueError:
        valid = ", ".join(pk.value for pk in PromptKey)
        return None, f"無効なプロンプトキー: `{key}`。有効な値: {valid}"


def _parse_github(
    raw: str | None, guild_id: int | None
) -> tuple[GitHub | None, str | None]:
    if guild_id is None:
        return None, "ギルドIDが指定されていません。"

    url = (raw or "").strip()
    if not url:
        return None, None
    parsed = urlparse(url)
    if (
        parsed.scheme not in ("http", "https")
        or "github.com" not in parsed.netloc.lower()
    ):
        return None, f"無効な GitHub URL: `{url}`"
    repo_name = _extract_repo_name(url)
    if not repo_name:
        return None, f"リポジトリ名の抽出に失敗: `{url}`"
    local_path = f"data/repo/{repo_name}_{guild_id}"
    return GitHub(repo_url=url, local_repo_path=local_path), None


def _parse_user_names(text: str | None) -> tuple[dict[str, str], list[str]]:
    errors: list[str] = []
    result: dict[str, str] = {}
    for line_ in filter(None, (line_.strip() for line_ in (text or "").splitlines())):
        if ":" in line_:
            k, v = line_.split(":", 1)
            result[k.strip()] = v.strip()
        else:
            errors.append(f"不正なユーザー名行: '{line_}'")
    return result, errors


def _parse_schedules(text: str | None) -> tuple[list[MeetingSchedule], list[str]]:
    errors: list[str] = []
    schedules: list[MeetingSchedule] = []
    for line_ in filter(None, (line_.strip() for line_ in (text or "").splitlines())):
        if ":" in line_:
            k, v = line_.split(":", 1)
            v = v.strip()
            schedule = parse_schedule_from_string(v)
            if schedule:
                schedules.append(
                    MeetingSchedule(channel_id=int(k.strip()), schedule=schedule)
                )
            else:
                errors.append(f"スケジュール行のパース失敗: '{line_}'")
        else:
            errors.append(f"スケジュール行のパース失敗: '{line_}'")
    return schedules, errors


def _to_text_user_names(user_names: Mapping[str, str]) -> str:
    return "\n".join(f"{k}:{v}" for k, v in user_names.items()) if user_names else ""


def _to_text_schedules(schedules: list[MeetingSchedule]) -> str:
    return (
        "\n".join(f"{s.channel_id}: {s.schedule.to_string()}" for s in schedules)
        if schedules
        else ""
    )


class ParametersModal(discord.ui.Modal):
    def __init__(self, title: str, initial_params: Parameters, guild_id: int) -> None:
        super().__init__(title=title)
        self.guild_id = guild_id
        self.initial_params = initial_params

        prompt_default = (
            initial_params.prompt_key.value if initial_params.prompt_key else "default"
        )
        self.prompt_key_input = discord.ui.InputText(
            label="プロンプトキー",
            placeholder="default, obsidian",
            value=prompt_default,
            max_length=50,
            required=False,
        )
        self.add_item(self.prompt_key_input)

        self.additional_context_input = discord.ui.InputText(
            label="追加コンテキスト",
            style=discord.InputTextStyle.long,
            placeholder="会議の背景情報や特別な指示を入力してください",
            value=initial_params.additional_context or "",
            max_length=1000,
            required=False,
        )
        self.add_item(self.additional_context_input)

        github = initial_params.github
        self.github_repo_url_input = discord.ui.InputText(
            label="GitHub リポジトリURL",
            placeholder="https://github.com/username/repository",
            value=github.repo_url if github else "",
            max_length=200,
            required=False,
        )
        self.add_item(self.github_repo_url_input)

        user_names_str = _to_text_user_names(initial_params.user_names or {})
        self.user_names_input = discord.ui.InputText(
            label="ユーザー名マッピング",
            style=discord.InputTextStyle.long,
            placeholder="例: user_id1:表示名1\nuser_id2:表示名2",
            value=user_names_str,
            max_length=1500,
            required=False,
        )
        self.add_item(self.user_names_input)

        schedule_str = _to_text_schedules(initial_params.schedules or [])
        self.schedules_input = discord.ui.InputText(
            label="スケジュール",
            style=discord.InputTextStyle.long,
            placeholder="例: <id>:weekly,mon,20:00 | <id>:biweekly,tue,15:00,2023-01-01 | <id>:monthly,1,18:30",
            value=schedule_str,
            max_length=1500,
            required=False,
        )
        self.add_item(self.schedules_input)

    async def callback(self, interaction: discord.Interaction):
        try:
            prompt_key, prompt_key_err = _parse_prompt_key(self.prompt_key_input.value)
            github_obj, github_err = _parse_github(
                self.github_repo_url_input.value, interaction.guild_id
            )
            user_names, user_name_errors = _parse_user_names(
                self.user_names_input.value
            )
            schedules, schedule_errors = _parse_schedules(self.schedules_input.value)

            additional_context = (
                self.additional_context_input.value or ""
            ).strip() or None

            if prompt_key_err:
                await interaction.response.send_message(prompt_key_err, ephemeral=True)
                return
            if github_err:
                await interaction.response.send_message(github_err, ephemeral=True)
                return

            new_params = Parameters(
                prompt_key=prompt_key,
                additional_context=additional_context,
                github=github_obj,
                user_names=user_names,
                schedules=schedules,
            )

            container.parameters_repository().set_parameters(self.guild_id, new_params)

            embed = create_parameters_embed(self.guild_id)
            await interaction.response.edit_message(embed=embed)

            nonfatal_errors = user_name_errors + schedule_errors
            if nonfatal_errors:
                msg = "以下の行はスキップされました:\n" + "\n".join(
                    f"- {e}" for e in nonfatal_errors
                )
                await interaction.followup.send(msg, ephemeral=True)

        except Exception:
            logger.exception("ParametersModal failed for guild %s", self.guild_id)
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="エラー",
                    description="パラメータ更新中にエラーが発生しました。",
                    color=discord.Color.red(),
                ),
                ephemeral=True,
            )
