from datetime import datetime
from pathlib import Path
from typing import Iterator

import discord
from post_process.post_process import PostProcess
from summarizer.prompt_provider.summarize_prompt_provider import (
    ContextualSummarizePromptProvider,
)
from summarizer.summarizer import Summarizer
from transcriber.transcriber import Transcriber

from handler.feature.attendees_handler import AttendeesHandler, NoAudioToMixError
from handler.feature.summarize import MeetingSummarizer
from handler.feature.transcribe import MeetingTranscriber
from handler.handler import (
    AUDIO_NOT_RECORDED,
    AudioHandler,
)
from types_ import Attendees, CreateThreadData, MessageData, SendData, SendThreadData
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
            transcription_path = handler.root / "transcription.txt"
            transcriber = MeetingTranscriber(self.transcriber)
            transcription = transcriber(
                mixed_file_path,
                output_file=transcription_path,
            )
            yield SendThreadData(
                embed=discord.Embed(description="文字起こしが完了しました。")
            )
        except Exception as e:
            yield SendThreadData(
                embed=discord.Embed(description=f"文字起こしに失敗しました: {e}")
            )
            return

        try:
            additional_context = handler.get_additional_context()
            self.summarize_prompt_provider.additional_context = additional_context

            summary_path = handler.root / "summary.md"
            summarizer = MeetingSummarizer(self.summarizer)
            summary = summarizer(
                transcription,
                output_file=summary_path,
            )
            embed = discord.Embed(
                title="議事録",
                description=summary,
                timestamp=datetime.now(),
            )
            view = CommitView(post_process=self.post_process)
            yield SendThreadData(
                embed=embed,
            )
            yield SendData(
                files=[
                    discord.File(transcription_path, "transcription.txt"),
                ],
                embed=embed,
                view=view,
            )
        except Exception as e:
            yield SendThreadData(content=f"要約に失敗しました: {e}")
            return
