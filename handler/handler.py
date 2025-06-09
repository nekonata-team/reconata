from abc import ABC, abstractmethod
from pathlib import Path
from typing import Iterator

from types_ import Attendees, MessageData

# COMMON MESSAGE TEMPLATES
AUDIO_NOT_RECORDED = "録音された音声がありません。"


class AudioHandler(ABC):
    encoding: str

    @abstractmethod
    def __call__(self, attendees: Attendees) -> Iterator[MessageData]:
        pass


class AudioHandlerFromCLI(ABC):
    @abstractmethod
    def __call__(
        self,
        mixed_audio_path: Path,
        context_path: Path,
    ) -> Iterator[MessageData]:
        pass
