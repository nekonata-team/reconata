import asyncio
from datetime import datetime
from pathlib import Path
from typing import cast

import discord
from nekomeeta.transcriber.transcriber import IterableTranscriber, Transcriber

from src.bot.attendee import Attendees

from .common import create_path_builder, get_attendees_ids_string, mix, save_all_audio
from .message_data import (
    CreateThreadData,
    EditMessageData,
    SendData,
    SendThreadData,
)
from .recording_handler import (
    AUDIO_NOT_RECORDED,
    AudioHandlerResult,
    RecordingHandler,
)


class TranscriptionAudioHandler(RecordingHandler):
    def __init__(
        self,
        transcriber: Transcriber,
        dir: Path = Path("./data"),
    ):
        self.dir = dir
        self.transcriber = transcriber

    async def __call__(self, attendees: Attendees) -> AudioHandlerResult:
        if not attendees:
            yield SendData(content=AUDIO_NOT_RECORDED)
            return

        today = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        yield CreateThreadData(
            name="録音議事録スレッド - " + today,
            auto_archive_duration=1440,
            type=discord.ChannelType.public_thread,
        )

        path_builder = create_path_builder(self.dir)

        yield SendThreadData(
            embed=discord.Embed(
                description=f"録音ファイルを処理しています。\n\n参加者:\n{get_attendees_ids_string(attendees)}",
            )
        )

        files = await asyncio.to_thread(save_all_audio, path_builder, attendees)

        try:
            mixed_file_path = await asyncio.to_thread(
                mix,
                files,
                path_builder.mixed_audio(),
            )
            yield SendThreadData(
                embed=discord.Embed(
                    description="ミックスされた音声ファイルを保存しました。",
                )
            )
        except Exception as e:
            yield SendThreadData(
                embed=discord.Embed(
                    description=f"音声ファイルのミックスに失敗しました: {e}",
                )
            )
            return

        yield SendThreadData(
            embed=discord.Embed(description="文字起こしを開始します。")
        )

        try:
            transcription_path = path_builder.transcription()

            if isinstance(self.transcriber, IterableTranscriber):
                lines, messages = self._transcribe_iter(
                    mixed_file_path,
                )
                async for message in messages:
                    yield message
                transcription = "\n".join(lines)
                with open(transcription_path, "w", encoding="utf-8") as f:
                    f.write(transcription)

            else:
                transcription, messages = self._transcribe_and_save(
                    mixed_file_path,
                    transcription_path,
                )
                async for message in messages:
                    yield message
        except Exception as e:
            yield SendThreadData(
                embed=discord.Embed(description=f"文字起こしに失敗しました: {e}")
            )
            return

        yield SendData(
            files=[discord.File(transcription_path, "transcription.txt")],
        )

    def _transcribe_and_save(
        self,
        mixed_file_path: Path,
        transcription_path: Path,
    ) -> tuple[str, AudioHandlerResult]:
        transcription = self.transcriber.transcribe(str(mixed_file_path))
        with open(transcription_path, "w", encoding="utf-8") as f:
            f.write(transcription)

        async def message_iter():
            yield SendThreadData(
                embed=discord.Embed(description="文字起こしが完了しました。")
            )

        return transcription, message_iter()

    def _transcribe_iter(
        self,
        mixed_file_path: Path,
    ) -> tuple[list[str], AudioHandlerResult]:
        segments = cast(IterableTranscriber, self.transcriber).transcribe_iter(
            str(mixed_file_path)
        )
        lines: list[str] = []

        async def message_iter():
            async for segment in segments:
                lines.append(segment.text)
                embed = discord.Embed(description="文字起こしの一部が保存されました。")
                embed.add_field(
                    name="進捗",
                    value=f"{segment.end:.2f} s",
                )
                embed.add_field(
                    name="プレビュー",
                    value=segment.text,
                )
                yield EditMessageData(embed=embed)

        return lines, message_iter()
