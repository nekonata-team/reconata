from abc import ABC, abstractmethod


class Summarizer(ABC):
    """議事録を作成するための要約機能の抽象基底クラス"""

    @abstractmethod
    def generate_meeting_notes(self, transcription: str) -> str:
        """テキスト化された内容から議事録を生成する"""
        pass
