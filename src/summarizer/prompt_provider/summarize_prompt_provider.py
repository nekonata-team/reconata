from abc import ABC, abstractmethod


class SummarizePromptProvider(ABC):
    """AI に対してプロンプトを提供するための抽象基底クラス"""

    @abstractmethod
    def get_prompt(self, transcription: str) -> str:
        """音声のテキスト化結果を受け取り、AI に対してプロンプトを生成する"""
        pass

    @abstractmethod
    def get_system_prompt(self) -> str:
        """AI に対してシステムプロンプトを提供する"""
        pass


class ContextualSummarizePromptProvider(SummarizePromptProvider):
    """追加のコンテキストを持つプロンプトを提供する抽象基底クラス"""

    def __init__(self, additional_context: str | None = None) -> None:
        super().__init__()
        self.additional_context = additional_context

    def get_prompt(self, transcription: str) -> str:
        return f"{self.additional_context or ''}\n文字起こし: {transcription}"
