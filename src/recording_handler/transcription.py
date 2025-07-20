import asyncio
from datetime import datetime
from pathlib import Path

import discord

from src.bot.attendee import Attendees
from src.transcriber.transcriber import Transcriber

from .common import create_path_builder, get_attendees_ids_string, mix, save_all_audio
from .message_data import (
    CreateThreadData,
    SendData,
    SendThreadData,
)
from .part import save_transcription
from .recording_handler import (
    AUDIO_NOT_RECORDED,
    AudioHandlerResult,
    RecordingHandler,
)


class TranscriptionRecordingHandler(RecordingHandler):
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
            async for message in save_transcription(
                mixed_file_path, transcription_path, self.transcriber
            ):
                yield message
        except Exception as e:
            yield SendThreadData(
                embed=discord.Embed(description=f"文字起こしに失敗しました: {e}")
            )
            return

        yield SendData(
            files=[discord.File(transcription_path, "transcription.txt")],
        )
