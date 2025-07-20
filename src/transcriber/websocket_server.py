import hashlib
import json
import os
import tempfile
from typing import Any

import websockets

from .message_types import (
    DEFAULT_WEBSOCKET_PORT,
    PING_TIMEOUT,
    EndOfAudioMessage,
    EndOfTranscriptionMessage,
    ErrorMessage,
    TranscriptionSegmentMessage,
    WebsocketMessage,
    parse_message,
)
from .transcriber import IterableTranscriber


class WebSocketIterableTranscriberServer:
    """
    WebSocket経由で音声ファイルの逐次文字起こしを提供するサーバー実装。
    クライアントから音声データをチャンクで受信し、一時ファイルに保存してTranscriberに渡す。
    """

    def __init__(
        self,
        transcriber: IterableTranscriber,
        host: str = "0.0.0.0",
        port: int = DEFAULT_WEBSOCKET_PORT,
        tmp_dir="./tmp",
    ):
        self.host = host
        self.port = port
        self.transcriber = transcriber
        self.tmp_dir = tmp_dir

    async def handler(self, websocket):
        os.makedirs(self.tmp_dir, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=self.tmp_dir) as tmpfile:
            while True:
                message = await websocket.recv()
                if isinstance(message, bytes):
                    # バイナリは音声チャンク
                    tmpfile.write(message)
                    continue
                data = json.loads(message)
                try:
                    msg: WebsocketMessage = parse_message(data)
                    match msg:
                        case EndOfAudioMessage(hash=client_hash):
                            tmpfile.flush()
                            # ハッシュ検証
                            tmpfile.seek(0)
                            hasher = hashlib.sha256()
                            while True:
                                chunk = tmpfile.read(512 * 1024)
                                if not chunk:
                                    break
                                hasher.update(chunk)
                            server_hash = hasher.hexdigest()
                            if client_hash and client_hash != server_hash:
                                await self._send(
                                    websocket,
                                    ErrorMessage(
                                        error=f"Audio hash mismatch: client={client_hash}, server={server_hash}"
                                    ),
                                )
                                return
                            break
                        case _:
                            await self._send(
                                websocket,
                                ErrorMessage(
                                    error=f"Invalid message type: {type(msg)}"
                                ),
                            )
                            return
                except Exception as e:
                    await self._send(
                        websocket, ErrorMessage(error=f"Invalid message format: {e}")
                    )
                    return
            audio_path = tmpfile.name
            # 逐次セグメントを送信
            try:
                async for segment in self.transcriber.transcribe_iter(audio_path):
                    await self._send(
                        websocket,
                        TranscriptionSegmentMessage(
                            start=segment.start,
                            end=segment.end,
                            text=segment.text,
                        ),
                    )
                await self._send(websocket, EndOfTranscriptionMessage())
            except Exception as e:
                await self._send(
                    websocket, ErrorMessage(error=f"Transcription error: {e}")
                )

    async def _send(self, websocket: Any, msg: WebsocketMessage) -> None:
        await websocket.send(json.dumps(msg.to_dict()))

    async def start_server(self) -> None:
        self._server = await websockets.serve(
            self.handler,
            self.host,
            self.port,
            max_size=8 * 1024 * 1024,
            ping_interval=PING_TIMEOUT,
            ping_timeout=PING_TIMEOUT,
        )
        print(
            f"WebSocketIterableTranscriberServer running on ws://{self.host}:{self.port}"
        )
        await self._server.wait_closed()

    def stop_server(self) -> None:
        if hasattr(self, "_server"):
            self._server.close()
