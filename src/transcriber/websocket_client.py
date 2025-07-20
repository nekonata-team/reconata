import json
from typing import Any, AsyncGenerator

import websockets

from .message_types import (
    DEFAULT_WEBSOCKET_PORT,
    PING_TIMEOUT,
    EndOfAudioMessage,
    EndOfTranscriptionMessage,
    TranscriptionSegmentMessage,
    WebsocketMessage,
    parse_message,
)
from .transcriber import IterableTranscriber, Segment


class WebSocketIterableTranscriberClient(IterableTranscriber):
    """
    WebSocket経由でサーバーに音声ファイルパスを送り、逐次セグメントを受信するクライアント実装。
    """

    def __init__(self, uri=f"ws://localhost:{DEFAULT_WEBSOCKET_PORT}"):
        self.uri = uri

    async def transcribe_iter(self, audio_path: str) -> AsyncGenerator[Segment, None]:
        async with websockets.connect(
            self.uri,
            max_size=8 * 1024 * 1024,
            ping_interval=PING_TIMEOUT,
            ping_timeout=PING_TIMEOUT,
        ) as websocket:
            await self._send_audio_chunks(websocket, audio_path)
            while True:
                message = await websocket.recv()
                if isinstance(message, bytes):
                    # バイナリはサーバーから返されない想定
                    continue
                data: dict = json.loads(message)
                msg: WebsocketMessage = parse_message(data)
                match msg:
                    case EndOfTranscriptionMessage():
                        break
                    case TranscriptionSegmentMessage(start=s, end=e, text=t):
                        yield Segment(start=s, end=e, text=t)
                    case _ if "error" in data:
                        raise RuntimeError(data["error"])

    async def _send_audio_chunks(
        self, websocket: Any, audio_path: str, chunk_size: int = 512 * 1024
    ) -> None:
        import hashlib

        hasher = hashlib.sha256()
        with open(audio_path, "rb") as f:
            while True:
                chunk: bytes = f.read(chunk_size)
                if not chunk:
                    break
                hasher.update(chunk)
                # バイナリフレームで直接送信
                await websocket.send(chunk)
        file_hash = hasher.hexdigest()
        await self._send(websocket, EndOfAudioMessage(hash=file_hash))

    async def _send(self, websocket: Any, msg: WebsocketMessage) -> None:
        await websocket.send(json.dumps(msg.to_dict()))
