from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from input_provider.context import NekonataContext
from pydub import AudioSegment

from handler.feature.path_builder import PathBuilder
from types_ import Attendees

_TZ = ZoneInfo("Asia/Tokyo")


class NoAudioToMixError(Exception):
    """ミックスする音声がない場合の例外"""

    pass


class AttendeesHandler:
    """
    Attendeesのデータをもとに副作用するクラス
    """

    def __init__(self, attendees: Attendees, dir: Path, encoding: str):
        self.attendees = attendees
        session_root = dir / datetime.now().strftime("%Y%m%d_%H%M%S")
        self.path_builder = PathBuilder(session_root, encoding)

    def save_all(self) -> list[Path]:
        output_files: list[Path] = []

        for user_id, data in self.attendees.items():
            audio = data.audio
            file_path = self.path_builder.user_audio(user_id)
            with open(file_path, "wb") as f:
                f.write(audio.file.read())
            output_files.append(file_path)

        return output_files

    def mix(self, files: list[Path]) -> Path:
        output_file = self.path_builder.mixed_audio()
        segments: list[AudioSegment] = [
            AudioSegment.from_file(file)
            for file in files
            if file.exists() and file.is_file()
        ]

        if not segments:
            raise NoAudioToMixError("ミックスする音声がありません。")

        segments = sorted(segments, key=lambda seg: seg.duration_seconds, reverse=True)
        mixed = segments[0]
        for seg in segments[1:]:
            mixed = mixed.overlay(seg)

        mixed.export(output_file)
        return output_file

    def get_attendees_ids_string(self) -> str:
        if not self.attendees:
            return "参加者がいません。"
        return "\n".join(f"- `{user_id}`" for user_id in self.attendees.keys())

    def get_additional_context(self) -> str:
        participant_names = ",".join(
            [
                NekonataContext.id2name.get(str(id), f"<@{id}>")
                for id in self.attendees.keys()
            ]
        )
        notes_joined = "\n".join(NekonataContext.notes)
        today_str = datetime.now(_TZ).strftime("%Y年%m月%d日")
        return f"録音日: {today_str}\n参加者: {participant_names}\n補足: {notes_joined}"
