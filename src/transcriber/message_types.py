from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum
from typing import Dict, Type

DEFAULT_WEBSOCKET_PORT = 8765
PING_TIMEOUT = 3600


class MessageType(StrEnum):
    AUDIO_CHUNK = "audio_chunk"
    END_OF_AUDIO = "end_of_audio"
    TRANSCRIPTION_SEGMENT = "transcription_segment"
    END_OF_TRANSCRIPTION = "end_of_transcription"
    ERROR = "error"


class WebsocketMessage(ABC):
    type: MessageType

    @abstractmethod
    def to_dict(self) -> dict:
        pass

    @classmethod
    @abstractmethod
    def from_dict(cls, obj: dict) -> "WebsocketMessage":
        pass


@dataclass(frozen=True)
class AudioChunkMessage(WebsocketMessage):
    data: str = ""
    type: MessageType = MessageType.AUDIO_CHUNK

    def to_dict(self):
        return {"type": self.type, "data": self.data}

    @classmethod
    def from_dict(cls, obj: dict) -> "AudioChunkMessage":
        if obj.get("type") != MessageType.AUDIO_CHUNK:
            raise ValueError("Not an audio_chunk message")
        return cls(data=obj["data"])


@dataclass(frozen=True)
class EndOfAudioMessage(WebsocketMessage):
    hash: str = ""
    type: MessageType = MessageType.END_OF_AUDIO

    def to_dict(self):
        return {"type": self.type, "hash": self.hash}

    @classmethod
    def from_dict(cls, obj: dict) -> "EndOfAudioMessage":
        if obj.get("type") != MessageType.END_OF_AUDIO:
            raise ValueError("Not an end_of_audio message")
        return cls(hash=obj.get("hash", ""))


@dataclass(frozen=True)
class TranscriptionSegmentMessage(WebsocketMessage):
    start: float = 0.0
    end: float = 0.0
    text: str = ""
    type: MessageType = MessageType.TRANSCRIPTION_SEGMENT

    def to_dict(self):
        return {
            "type": self.type,
            "start": self.start,
            "end": self.end,
            "text": self.text,
        }

    @classmethod
    def from_dict(cls, obj: dict) -> "TranscriptionSegmentMessage":
        return cls(start=obj["start"], end=obj["end"], text=obj["text"])


@dataclass(frozen=True)
class EndOfTranscriptionMessage(WebsocketMessage):
    end_of_transcription: bool = True
    type: MessageType = MessageType.END_OF_TRANSCRIPTION

    def to_dict(self):
        return {"type": self.type, "end_of_transcription": self.end_of_transcription}

    @classmethod
    def from_dict(cls, obj: dict) -> "EndOfTranscriptionMessage":
        return cls(end_of_transcription=obj["end_of_transcription"])


@dataclass(frozen=True)
class ErrorMessage(WebsocketMessage):
    error: str = ""
    type: MessageType = MessageType.ERROR

    def to_dict(self):
        return {"type": self.type, "error": self.error}

    @classmethod
    def from_dict(cls, obj: dict) -> "ErrorMessage":
        return cls(error=obj["error"])


MESSAGE_TYPE_TO_CLASS: Dict[str, Type[WebsocketMessage]] = {
    MessageType.AUDIO_CHUNK: AudioChunkMessage,
    MessageType.END_OF_AUDIO: EndOfAudioMessage,
    MessageType.TRANSCRIPTION_SEGMENT: TranscriptionSegmentMessage,
    MessageType.END_OF_TRANSCRIPTION: EndOfTranscriptionMessage,
    MessageType.ERROR: ErrorMessage,
}


def parse_message(obj: dict) -> WebsocketMessage:
    msg_type = obj.get("type")
    msg_type = MessageType(msg_type)
    cls = MESSAGE_TYPE_TO_CLASS.get(msg_type)
    if cls is None:
        raise ValueError(f"Unknown message type: {msg_type}")
    return cls.from_dict(obj)
