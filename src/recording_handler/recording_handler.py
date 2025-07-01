from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator

from src.bot.attendee import Attendees

from .message_data import MessageData

# COMMON MESSAGE TEMPLATES
AUDIO_NOT_RECORDED = "録音された音声がありません。"


AudioHandlerResult = AsyncGenerator[MessageData, None]


class RecordingHandler(ABC):
    @abstractmethod
    async def __call__(self, attendees: Attendees) -> AudioHandlerResult:
        yield  # type: ignore[return]
