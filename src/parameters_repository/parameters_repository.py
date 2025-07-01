from abc import ABC, abstractmethod
from typing import Mapping

from pydantic import BaseModel, Field

from src.bot.enums import PromptKey


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
    github_repo_url: str | None = Field(
        default=None, description="GitHubリポジトリのURL"
    )
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
