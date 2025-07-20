import time
from pathlib import Path

import discord

from src.transcriber.transcriber import IterableTranscriber, Transcriber

from .message_data import EditMessageData, SendThreadData
from .recording_handler import AudioHandlerResult


async def save_transcription(
    mixed_file_path: Path,
    transcription_path: Path,
    transcriber: Transcriber | IterableTranscriber,
) -> AudioHandlerResult:
    if isinstance(transcriber, IterableTranscriber):
        lines, messages = _transcribe_iter(
            mixed_file_path,
            transcriber,
        )
        async for message in messages:
            yield message
        transcription = "\n".join(lines)
        with open(transcription_path, "w", encoding="utf-8") as f:
            f.write(transcription)

    else:
        transcription, messages = _transcribe_and_save(
            mixed_file_path, transcription_path, transcriber
        )
        async for message in messages:
            yield message


def _transcribe_and_save(
    mixed_file_path: Path,
    transcription_path: Path,
    transcriber: Transcriber,
) -> tuple[str, AudioHandlerResult]:
    transcription = transcriber.transcribe(str(mixed_file_path))
    with open(transcription_path, "w", encoding="utf-8") as f:
        f.write(transcription)

    async def message_iter():
        yield SendThreadData(
            embed=discord.Embed(description="文字起こしが完了しました。")
        )

    return transcription, message_iter()


def _transcribe_iter(
    mixed_file_path: Path,
    transcriber: IterableTranscriber,
) -> tuple[list[str], AudioHandlerResult]:
    segments = transcriber.transcribe_iter(str(mixed_file_path))
    lines: list[str] = []

    async def message_iter():
        last_yield_time = time.monotonic()
        last_segment = None

        async for segment in segments:
            lines.append(segment.text)
            last_segment = segment
            current_time = time.monotonic()

            if current_time - last_yield_time >= 1.0:
                embed = discord.Embed(description="文字起こしの一部が保存されました。")
                embed.add_field(name="進捗", value=f"{segment.end:.2f} s")
                embed.add_field(name="プレビュー", value=segment.text)
                yield EditMessageData(embed=embed)
                last_yield_time = current_time

        if last_segment:
            embed = discord.Embed(description="文字起こしが完了しました。")
            embed.add_field(name="進捗", value=f"{last_segment.end:.2f} s")
            embed.add_field(name="プレビュー", value=last_segment.text)
            yield EditMessageData(embed=embed)

    return lines, message_iter()
