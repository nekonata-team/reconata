from pathlib import Path
from typing import Annotated, cast, get_args

import click
import typer
from nekomeeta.transcriber.faster_whisper import (
    ComputeType,
    FasterWhisperModelSize,
)

from src.cli.embed import handle_embed_command
from src.cli.send import handle_send_command
from src.cli.websocket import handle_websocket_command

app = typer.Typer(help="Discord Bot CLI")


@app.command()
def send(
    mixed_audio_path: Annotated[
        Path,
        typer.Argument(help="ミックスされた音声ファイルのパス", exists=True),
    ],
    context_path: Annotated[
        Path,
        typer.Argument(help="コンテキスト情報が含まれるファイルのパス", exists=True),
    ],
    channel_url: Annotated[
        str,
        typer.Argument(help="メッセージを送信するDiscordチャンネルのURL"),
    ],
) -> None:
    """Discordチャンネルに音声メッセージを送信"""
    handle_send_command(mixed_audio_path, context_path, channel_url)


@app.command()
def embed(
    message_url: Annotated[
        str,
        typer.Argument(help="取得したいDiscordメッセージのURL"),
    ],
) -> None:
    """Discordメッセージのembed descriptionを表示"""
    handle_embed_command(message_url)


@app.command()
def websocket(
    host: Annotated[
        str,
        typer.Option("--host", help="WebSocketサーバーのホストアドレス"),
    ] = "0.0.0.0",
    port: Annotated[
        int,
        typer.Option("--port", help="WebSocketサーバーのポート番号"),
    ] = 9876,
    model_size: Annotated[
        str,
        typer.Option(
            "--model-size",
            help="Whisperモデルサイズ",
            click_type=click.Choice(get_args(FasterWhisperModelSize)),
        ),
    ] = "large-v3",
    compute_type: Annotated[
        str,
        typer.Option(
            "--compute-type",
            help="計算タイプ",
            click_type=click.Choice(get_args(ComputeType)),
        ),
    ] = "int8",
    beam_size: Annotated[
        int,
        typer.Option("--beam-size", help="ビームサイズ"),
    ] = 5,
    hotwords: Annotated[
        str, typer.Option("--hotwords", help="ホットワード")
    ] = "nekonata",
) -> None:
    """WebSocketトランスクライバーサーバーを起動"""
    handle_websocket_command(
        host,
        port,
        cast(FasterWhisperModelSize, model_size),
        cast(ComputeType, compute_type),
        beam_size,
        hotwords,
    )


if __name__ == "__main__":
    app()
