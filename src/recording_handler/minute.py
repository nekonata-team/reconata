import asyncio
from datetime import datetime
from logging import getLogger
from pathlib import Path
from typing import cast

import discord
from nekomeeta.summarizer.formatter.summary_formatter import SummaryFormatter
from nekomeeta.summarizer.prompt_provider.summarize_prompt_provider import (
    ContextualSummarizePromptProvider,
)
from nekomeeta.summarizer.summarizer import Summarizer
from nekomeeta.transcriber.transcriber import IterableTranscriber, Transcriber

from src.bot.type import Attendees
from src.ui.view_builder import ViewBuilder

from .common import create_path_builder, get_context, mix, save_all_audio
from .message_data import (
    CreateThreadData,
    EditMessageData,
    SendData,
    SendThreadData,
)
from .path_builder import PathBuilder
from .recording_handler import (
    AUDIO_NOT_RECORDED,
    AudioHandlerResult,
    RecordingHandler,
)

logger = getLogger(__name__)


class MinuteAudioHandler(RecordingHandler):
    def __init__(
        self,
        dir: Path,
        transcriber: Transcriber | IterableTranscriber,
        summarizer: Summarizer,
        summarize_prompt_provider: ContextualSummarizePromptProvider,
        summary_formatter: SummaryFormatter,
        view_builder: ViewBuilder,
    ):
        self.dir = dir
        self.transcriber = transcriber
        self.summarizer = summarizer
        self.summarize_prompt_provider = summarize_prompt_provider
        self.summary_formatter = summary_formatter
        self.view_builder = view_builder

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
        context = get_context(list(attendees.keys()))

        yield SendThreadData(
            embed=discord.Embed(
                title="議事録のコンテキスト",
                description=context,
                timestamp=datetime.now(),
            )
        )

        yield SendThreadData(
            embed=discord.Embed(description="録音ファイルを処理しています。")
        )

        files = await asyncio.to_thread(save_all_audio, path_builder, attendees)

        try:
            mixed_file_path = await asyncio.to_thread(
                mix, files, path_builder.mixed_audio()
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

        async for message in self.handle_mixed_audio(
            path_builder,
            mixed_file_path,
            context,
        ):
            yield message

    async def handle_mixed_audio(
        self,
        path_builder: PathBuilder,
        mixed_file_path: Path,
        context: str,
    ) -> AudioHandlerResult:
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

        try:
            summary_path = path_builder.summary()
            summary, messages = self._summarize_and_save(
                summary_path,
                transcription,
                context,
            )
            async for message in messages:
                yield message
        except Exception as e:
            yield SendThreadData(content=f"要約に失敗しました: {e}")
            return

        yield self._create_final_send_data(
            transcription_path,
            self.summary_formatter.format(summary),
            self.view_builder,
        )

    def _transcribe_and_save(
        self,
        mixed_file_path: Path,
        transcription_path: Path,
    ) -> tuple[str, AudioHandlerResult]:
        transcription = cast(Transcriber, self.transcriber).transcribe(
            str(mixed_file_path)
        )
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

    def _summarize_and_save(
        self,
        summary_path: Path,
        transcription: str,
        context: str,
    ) -> tuple[str, AudioHandlerResult]:
        self.summarize_prompt_provider.additional_context = context
        summary = self.summarizer.generate_meeting_notes(transcription)
        with open(summary_path, "w", encoding="utf-8") as f:
            f.write(summary)
        embed = discord.Embed(
            description=summary,
            timestamp=datetime.now(),
        )

        async def message_iter():
            yield SendThreadData(
                embed=embed,
            )

        return summary, message_iter()

    def _create_final_send_data(
        self,
        transcription_path: Path,
        summary: str,
        view_builder: ViewBuilder,
    ) -> SendData:
        now = datetime.now()
        embed = discord.Embed(
            title=now.strftime("%Y年%m月%d日"),
            description=summary,
            timestamp=now,
        )
        view = view_builder.create_view()

        logger.info("Embed created.")

        return SendData(
            files=[discord.File(transcription_path, "transcription.txt")],
            embed=embed,
            view=view,
        )
