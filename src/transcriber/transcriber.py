from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import AsyncGenerator


class Transcriber(ABC):
    """音声をテキスト化するための抽象基底クラス"""

    @abstractmethod
    def transcribe(self, audio_path: str) -> str:
        """指定された音声ファイルをテキスト化する"""
        pass


@dataclass
class Segment:
    """音声のセグメントを表すデータクラス"""

    start: float
    end: float
    text: str


class IterableTranscriber(ABC):
    """音声ファイルを複数のテキストチャンクに分割して返すための抽象基底クラス"""

    @abstractmethod
    async def transcribe_iter(self, audio_path: str) -> AsyncGenerator[Segment, None]:
        """指定された音声ファイルを複数のテキストチャンクとして逐次的に返す（async generator）"""
        yield  # type: ignore
