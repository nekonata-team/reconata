from datetime import datetime
from logging import getLogger
from pathlib import Path
from typing import cast

import discord
from nekomeeta.post_process.github_push import GitHubPusher
from nekomeeta.summarizer.formatter.summary_formatter import SummaryFormatter
from nekomeeta.summarizer.prompt_provider.summarize_prompt_provider import (
    ContextualSummarizePromptProvider,
)
from nekomeeta.summarizer.summarizer import Summarizer
from nekomeeta.transcriber.transcriber import IterableTranscriber, Transcriber

from types_ import (
    Attendees,
    CreateThreadData,
    EditMessageData,
    SendData,
    SendThreadData,
)
from view import CommitView

from .audio_handler import (
    AUDIO_NOT_RECORDED,
    AudioHandler,
    AudioHandlerFromCLI,
    AudioHandlerResult,
)
from .feature.attendees_handler import AttendeesHandler
from .feature.path_builder import PathBuilder

logger = getLogger(__name__)


class MinuteAudioHandler(AudioHandler):
    def __init__(
        self,
        dir: Path,
        transcriber: Transcriber | IterableTranscriber,
        summarizer: Summarizer,
        summarize_prompt_provider: ContextualSummarizePromptProvider,
        summary_formatter: SummaryFormatter,
        pusher: GitHubPusher,
    ):
        self.dir = dir
        self.transcriber = transcriber
        self.summarizer = summarizer
        self.summarize_prompt_provider = summarize_prompt_provider
        self.summary_formatter = summary_formatter
        self.pusher = pusher

    async def __call__(self, attendees: Attendees) -> AudioHandlerResult:
        today = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        yield CreateThreadData(
            name="録音議事録スレッド - " + today,
            auto_archive_duration=1440,
            type=discord.ChannelType.public_thread,
        )

        if not attendees:
            yield SendThreadData(content=AUDIO_NOT_RECORDED)
            return

        handler = AttendeesHandler(attendees, self.dir, self.encoding)

        context = handler.save_context()
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

        files = handler.save_all_audio()

        try:
            mixed_file_path = handler.mix(files)
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
            transcription_path = handler.path_builder.transcription()

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
            summary_path = handler.path_builder.summary()
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

        yield _create_final_send_data(
            transcription_path,
            self.summary_formatter.format(summary),
            self.pusher,
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


class MinuteAudioHandlerFromCLI(AudioHandlerFromCLI):
    def __init__(
        self,
        dir: Path,
        transcriber: Transcriber,
        summarizer: Summarizer,
        summarize_prompt_provider: ContextualSummarizePromptProvider,
        summary_formatter: SummaryFormatter,
        pusher: GitHubPusher,
    ):
        self.dir = dir
        self.transcriber = transcriber
        self.summarizer = summarizer
        self.summarize_prompt_provider = summarize_prompt_provider
        self.summary_formatter = summary_formatter
        self.pusher = pusher

    async def __call__(
        self,
        mixed_audio_path: Path,
        context_path: Path,
    ) -> AudioHandlerResult:
        path_builder = PathBuilder(self.dir, "---")

        transcription_path = path_builder.transcription()

        logger.info(
            f"Transcribing audio from {mixed_audio_path} to {transcription_path}"
        )

        if isinstance(self.transcriber, IterableTranscriber):
            transcription = ""
            async for segment in self.transcriber.transcribe_iter(
                str(mixed_audio_path)
            ):
                transcription += segment.text + "\n"
            with open(transcription_path, "w", encoding="utf-8") as f:
                f.write(transcription)
        else:
            transcription = self.transcriber.transcribe(str(mixed_audio_path))
            with open(transcription_path, "w", encoding="utf-8") as f:
                f.write(transcription)

        logger.info("Transcription completed.")
        logger.info(
            f"Summarizing transcription from {transcription_path} with context from {context_path}"
        )

        summary_path = path_builder.summary()
        self.summarize_prompt_provider.additional_context = context_path.read_text()

        summary = self.summary_formatter.format(
            self.summarizer.generate_meeting_notes(transcription)
        )
        with open(summary_path, "w", encoding="utf-8") as f:
            f.write(summary)

        logger.info("Summary completed.")

        yield _create_final_send_data(transcription_path, summary, self.pusher)


def _create_final_send_data(
    transcription_path: Path,
    summary: str,
    pusher: GitHubPusher,
) -> SendData:
    now = datetime.now()
    embed = discord.Embed(
        title=now.strftime("%Y年%m月%d日"),
        description=summary,
        timestamp=now,
    )
    view = CommitView(pusher=pusher)

    logger.info("Embed created.")

    return SendData(
        files=[discord.File(transcription_path, "transcription.txt")],
        embed=embed,
        view=view,
    )
