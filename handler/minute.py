from datetime import datetime
from pathlib import Path
from typing import Iterator, cast

import discord
from post_process.post_process import PostProcess
from summarizer.prompt_provider.summarize_prompt_provider import (
    ContextualSummarizePromptProvider,
)
from summarizer.summarizer import Summarizer
from transcriber.transcriber import IterableTranscriber, Transcriber

from handler.feature.attendees_handler import AttendeesHandler, NoAudioToMixError
from handler.handler import (
    AUDIO_NOT_RECORDED,
    AudioHandler,
)
from types_ import (
    Attendees,
    CreateThreadData,
    EditMessageData,
    MessageData,
    SendData,
    SendThreadData,
)
from view import CommitView


class MinuteAudioHandler(AudioHandler):
    def __init__(
        self,
        dir: Path,
        transcriber: Transcriber,
        summarizer: Summarizer,
        summarize_prompt_provider: ContextualSummarizePromptProvider,
        post_process: PostProcess,
        encoding: str = "wav",
    ):
        self.dir = dir
        self.transcriber = transcriber
        self.summarizer = summarizer
        self.summarize_prompt_provider = summarize_prompt_provider
        self.post_process = post_process

        self.encoding = encoding

    def __call__(self, attendees: Attendees) -> Iterator[MessageData]:
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

        yield SendThreadData(
            embed=discord.Embed(
                description=f"録音ファイルを処理しています。\n\n参加者:\n{handler.get_attendees_ids_string()}",
            )
        )

        files = handler.save_all()

        try:
            mixed_file_path = handler.mix(files)
            yield SendThreadData(
                embed=discord.Embed(
                    description="ミックスされた音声ファイルを保存しました。",
                )
            )
        except NoAudioToMixError as e:
            yield SendThreadData(
                embed=discord.Embed(
                    description=str(e),
                )
            )
            return
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
                yield from messages
                transcription = "\n".join(lines)
                with open(transcription_path, "w", encoding="utf-8") as f:
                    f.write(transcription)

            else:
                transcription, messages = self._transcribe_and_save(
                    mixed_file_path,
                    transcription_path,
                )
                yield from messages
        except Exception as e:
            yield SendThreadData(
                embed=discord.Embed(description=f"文字起こしに失敗しました: {e}")
            )
            return

        try:
            summary_path = handler.path_builder.summary()
            additional_context = handler.get_additional_context()
            summary, messages = self._summarize_and_save(
                summary_path,
                transcription,
                additional_context,
            )
            yield from messages
        except Exception as e:
            yield SendThreadData(content=f"要約に失敗しました: {e}")
            return

        embed = discord.Embed(
            title="要約",
            description=summary,
            timestamp=datetime.now(),
        )
        view = CommitView(post_process=self.post_process)
        yield SendData(
            files=[discord.File(transcription_path, "transcription.txt")],
            embed=embed,
            view=view,
        )

    def _transcribe_and_save(
        self,
        mixed_file_path: Path,
        transcription_path: Path,
    ) -> tuple[str, Iterator[MessageData]]:
        transcription = self.transcriber.transcribe(str(mixed_file_path))
        with open(transcription_path, "w", encoding="utf-8") as f:
            f.write(transcription)

        def message_iter():
            yield SendThreadData(
                embed=discord.Embed(description="文字起こしが完了しました。")
            )

        return transcription, message_iter()

    def _transcribe_iter(
        self,
        mixed_file_path: Path,
    ) -> tuple[list[str], Iterator[MessageData]]:
        segments = cast(IterableTranscriber, self.transcriber).transcribe_iter(
            str(mixed_file_path)
        )
        lines: list[str] = []

        def message_iter():
            for segment in segments:
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
    ) -> tuple[str, Iterator[MessageData]]:
        self.summarize_prompt_provider.additional_context = context
        summary = self.summarizer.generate_meeting_notes(transcription)
        with open(summary_path, "w", encoding="utf-8") as f:
            f.write(summary)
        embed = discord.Embed(
            description=summary,
            timestamp=datetime.now(),
        )

        def message_iter():
            yield SendThreadData(
                embed=embed,
            )

        return summary, message_iter()
