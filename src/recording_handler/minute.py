import asyncio
from datetime import datetime
from logging import getLogger
from pathlib import Path

import discord

from src.bot.attendee import Attendees
from src.summarizer.formatter.summary_formatter import SummaryFormatter
from src.summarizer.prompt_provider.summarize_prompt_provider import (
    ContextualSummarizePromptProvider,
)
from src.summarizer.summarizer import Summarizer
from src.transcriber.transcriber import IterableTranscriber, Transcriber
from src.ui.view_builder import ViewBuilder

from .common import create_path_builder, mix, save_all_audio
from .context_provider import ContextProvider
from .message_data import (
    CreateThreadData,
    SendData,
    SendThreadData,
)
from .part import save_transcription
from .path_builder import PathBuilder
from .recording_handler import (
    AUDIO_NOT_RECORDED,
    AudioHandlerResult,
    RecordingHandler,
)

logger = getLogger(__name__)


class MinuteRecordingHandler(RecordingHandler):
    def __init__(
        self,
        transcriber: Transcriber | IterableTranscriber,
        summarizer: Summarizer,
        summarize_prompt_provider: ContextualSummarizePromptProvider,
        summary_formatter: SummaryFormatter,
        view_builder: ViewBuilder,
        context_provider: ContextProvider,
        dir: Path = Path("./data"),
    ):
        self.dir = dir
        self.transcriber = transcriber
        self.summarizer = summarizer
        self.summarize_prompt_provider = summarize_prompt_provider
        self.summary_formatter = summary_formatter
        self.view_builder = view_builder
        self.context_provider = context_provider

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
        context = self.context_provider(list(attendees.keys()))

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
            async for message in save_transcription(
                mixed_file_path, transcription_path, self.transcriber
            ):
                yield message
        except Exception as e:
            yield SendThreadData(
                embed=discord.Embed(description=f"文字起こしに失敗しました: {e}")
            )
            return

        try:
            transcription = transcription_path.read_text(encoding="utf-8")
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

    def _summarize_and_save(
        self,
        summary_path: Path,
        transcription: str,
        context: str,
    ) -> tuple[str, AudioHandlerResult]:
        self.summarize_prompt_provider.additional_context = context
        summary_content = self.summarizer.generate_meeting_notes(transcription).content
        with open(summary_path, "w", encoding="utf-8") as f:
            f.write(summary_content)
        embed = discord.Embed(
            description=summary_content,
            timestamp=datetime.now(),
        )

        async def message_iter():
            yield SendThreadData(
                embed=embed,
            )

        return summary_content, message_iter()

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
