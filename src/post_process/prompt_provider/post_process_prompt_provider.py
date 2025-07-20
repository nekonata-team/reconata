from abc import ABC, abstractmethod


class PostProcessPromptProvider(ABC):
    """AI に対してプロンプトを提供するための抽象基底クラス"""

    @abstractmethod
    def get_prompt(self, meeting_notes: str) -> str:
        """議事録に対して、AI に対してプロンプトを生成する"""
        pass
