from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Iterator
from zoneinfo import ZoneInfo

import discord
from input_provider.context import NekonataContext
from post_process.post_process import PostProcess
from pydub import AudioSegment
from summarizer.prompt_provider.summarize_prompt_provider import (
    ContextualSummarizePromptProvider,
)
from summarizer.summarizer import Summarizer
from transcriber.transcriber import Transcriber

from types_ import (
    Attendees,
    CreateThreadData,
    MessageData,
    SendData,
    SendThreadData,
)
from view import CommitView

# COMMON MESSAGE TEMPLATES
_AUDIO_NOT_RECORDED = "録音された音声がありません。"

_TZ = ZoneInfo("Asia/Tokyo")


def _get_attendees_list(attendees: Attendees) -> str:
    if not attendees:
        return "参加者がいません。"
    return "\n".join(f"- `{user_id}`" for user_id in attendees.keys())


class AudioHandler(ABC):
    @abstractmethod
    def __call__(self, attendees: Attendees) -> Iterator[MessageData]:
        pass


class DiscordFileAudioHandler(AudioHandler):
    def __init__(self, encoding: str = "wav"):
        self.encoding = encoding

    def __call__(self, attendees: Attendees) -> Iterator[MessageData]:
        if not attendees:
            yield SendData(content=_AUDIO_NOT_RECORDED)
            return

        files = [
            discord.File(data.audio.file, f"{user_id}.{self.encoding}")
            for user_id, data in attendees.items()
        ]
        content = f"録音が完了しました。\n\n参加者:\n{_get_attendees_list(attendees)}"
        yield SendData(content=content, files=files)


class AudioFilePathBuilder:
    @staticmethod
    def user_audio_path(folder: Path, user_id: int, ext: str) -> Path:
        return folder / f"{user_id}.{ext}"

    @staticmethod
    def mixed_audio_path(folder: Path, ext: str) -> Path:
        return folder / f"mixed.{ext}"

    @staticmethod
    def user_id_from_path(path: Path) -> int:
        try:
            return int(path.stem)
        except Exception:
            raise ValueError(f"Invalid audio file name: {path.name}")

    @staticmethod
    def session_root_path(base_folder: Path, dt: datetime) -> Path:
        return base_folder / dt.strftime("%Y%m%d_%H%M%S")


def _mkdir(folder_path: Path) -> None:
    folder_path.mkdir(parents=True, exist_ok=True)


def _save_audio_files(
    audio_data: Attendees, folder_path: Path, encoding: str
) -> list[Path]:
    output_paths: list[Path] = []

    for user_id, data in audio_data.items():
        audio = data.audio
        file_path = AudioFilePathBuilder.user_audio_path(folder_path, user_id, encoding)
        with open(file_path, "wb") as f:
            f.write(audio.file.read())
        output_paths.append(file_path)

    return output_paths


class NoAudioToMixError(Exception):
    """ミックスする音声がない場合の例外"""

    pass


def _mix_audio_files(files: list[Path], output_file: Path) -> None:
    segments: list[AudioSegment] = [AudioSegment.from_file(file) for file in files]

    if not segments:
        raise NoAudioToMixError("ミックスする音声がありません。")

    segments = sorted(segments, key=lambda seg: seg.duration_seconds, reverse=True)
    mixed = segments[0]
    for seg in segments[1:]:
        mixed = mixed.overlay(seg)

    mixed.export(output_file)


def _transcribe_audio_file(
    transcriber: Transcriber, input_file: Path, output_file: Path | None
) -> str:
    transcription = transcriber.transcribe(str(input_file))
    if output_file is not None:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(transcription)

    return transcription


def _summarize_transcription(
    summarizer: Summarizer,
    transcription: str,
    output_file: Path | None = None,
):
    summary = summarizer.generate_meeting_notes(transcription)
    if output_file is not None:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(summary)

    return summary


class SaveToFolderAudioHandler(AudioHandler):
    def __init__(self, folder_path: Path, encoding: str = "wav"):
        self.folder_path = folder_path
        self.encoding = encoding

    def __call__(self, attendees: Attendees) -> Iterator[MessageData]:
        if not attendees:
            yield SendData(content=_AUDIO_NOT_RECORDED)
            return

        _mkdir(self.folder_path)
        files = _save_audio_files(attendees, self.folder_path, self.encoding)

        content = f"録音ファイルの保存が完了しました。\n\n参加者:\n{_get_attendees_list(attendees)}"
        yield SendData(content=content, files=[discord.File(file) for file in files])


class MinuteAudioHandler(AudioHandler):
    def __init__(
        self,
        folder_path: Path,
        transcriber: Transcriber,
        summarizer: Summarizer,
        summarize_prompt_provider: ContextualSummarizePromptProvider,
        post_process: PostProcess,
        encoding: str = "wav",
    ):
        self.folder_path = folder_path
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
            yield SendThreadData(content=_AUDIO_NOT_RECORDED)
            return

        yield SendThreadData(
            embed=discord.Embed(
                description=f"録音ファイルを処理しています。\n\n参加者:\n{_get_attendees_list(attendees)}",
            )
        )

        now = datetime.now()
        root = AudioFilePathBuilder.session_root_path(self.folder_path, now)

        _mkdir(root)
        files = _save_audio_files(attendees, root, self.encoding)

        mixed_file_path = AudioFilePathBuilder.mixed_audio_path(root, self.encoding)
        try:
            _mix_audio_files(files, mixed_file_path)
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

        transcription_path = root / "transcription.txt"
        try:
            transcription = _transcribe_audio_file(
                self.transcriber,
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

        ids = list(attendees.keys())
        additional_context = self._get_additional_context(ids)
        self.summarize_prompt_provider.additional_context = additional_context

        summary_path = root / "summary.md"
        try:
            summary = _summarize_transcription(
                self.summarizer,
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

    @staticmethod
    def _get_additional_context(ids: list[int]) -> str:
        participant_names = ",".join(
            [NekonataContext.id2name.get(str(id), f"<@{id}>") for id in ids]
        )
        notes_joined = "\n".join(NekonataContext.notes)
        today_str = datetime.now(_TZ).strftime("%Y年%m月%d日")
        return f"録音日: {today_str}\n参加者: {participant_names}\n補足: {notes_joined}"
