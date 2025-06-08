from abc import ABC, abstractmethod
from typing import Iterator

from types_ import Attendees, MessageData

# COMMON MESSAGE TEMPLATES
AUDIO_NOT_RECORDED = "録音された音声がありません。"


class AudioHandler(ABC):
    encoding: str

    @abstractmethod
    def __call__(self, attendees: Attendees) -> Iterator[MessageData]:
        pass
