from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class Summary:
    content: str
    input_token_count: int
    output_token_count: int


class Summarizer(ABC):
    """議事録を作成するための抽象基底クラス"""

    @abstractmethod
    def generate_meeting_notes(self, transcription: str) -> Summary:
        """文字起こしから議事録を生成する"""
        pass
