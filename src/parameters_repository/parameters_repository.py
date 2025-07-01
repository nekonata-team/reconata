from abc import ABC, abstractmethod
from typing import Mapping

from pydantic import BaseModel, Field

from src.bot.enums import PromptKey


class GitHub(BaseModel):
    repo_url: str = Field(description="GitHubリポジトリのURL")
    local_repo_path: str = Field(description="GitHubリポジトリのローカルパス")

    model_config = {"frozen": True}


class Parameters(BaseModel):
    prompt_key: PromptKey | None = Field(
        default=None, description="使用するプロンプトのキー"
    )
    user_names: Mapping[str, str] = Field(
        default_factory=dict, description="ユーザー名の辞書"
    )
    additional_context: str | None = Field(
        default=None, description="追加のコンテキスト情報"
    )
    github: GitHub | None = Field(default=None, description="GitHub関連の情報")
    hotwords: str | None = Field(default=None, description="文字起こし時のホットワード")

    model_config = {"frozen": True}


class ParametersRepository(ABC):
    @abstractmethod
    def get_parameters(self, guild_id: int) -> Parameters:
        pass

    @abstractmethod
    def reset_parameters(self, guild_id: int) -> None:
        pass

    @abstractmethod
    def set_parameters(self, guild_id: int, parameters: Parameters) -> None:
        pass
