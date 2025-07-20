import asyncio

import typer

from src.transcriber.faster_whisper import (
    ComputeType,
    FasterWhisperModelSize,
    FasterWhisperTranscriber,
)
from src.transcriber.transcriber import IterableTranscriber
from src.transcriber.websocket_server import WebSocketIterableTranscriberServer


def handle_websocket_command(
    host: str,
    port: int,
    model_size: FasterWhisperModelSize,
    compute_type: ComputeType,
    beam_size: int,
    batch_size: int,
    hotwords: str,
) -> None:
    typer.echo("WebSocketトランスクライバーサーバーを起動中...")
    typer.echo(f"ホスト: {host}")
    typer.echo(f"ポート: {port}")
    typer.echo(f"モデル: {model_size}")

    transcriber = FasterWhisperTranscriber(
        model_size=model_size,
        compute_type=compute_type,
        beam_size=beam_size,
        batch_size=batch_size,
        hotwords=hotwords,
    )

    asyncio.run(_run_server(transcriber, host, port))


async def _run_server(transcriber: IterableTranscriber, host: str, port: int) -> None:
    server = WebSocketIterableTranscriberServer(
        transcriber=transcriber, host=host, port=port
    )
    await server.start_server()
