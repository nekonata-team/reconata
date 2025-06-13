from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from pathlib import Path

from types_ import Attendees, MessageData

# COMMON MESSAGE TEMPLATES
AUDIO_NOT_RECORDED = "録音された音声がありません。"


AudioHandlerResult = AsyncGenerator[MessageData, None]


class AudioHandler(ABC):
    encoding: str

    @abstractmethod
    async def __call__(self, attendees: Attendees) -> AudioHandlerResult:
        yield  # type: ignore[return]


class AudioHandlerFromCLI(ABC):
    @abstractmethod
    async def __call__(
        self,
        mixed_audio_path: Path,
        context_path: Path,
    ) -> AudioHandlerResult:
        yield  # type: ignore[return]
