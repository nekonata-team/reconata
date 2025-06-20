from datetime import datetime
from logging import getLogger
from pathlib import Path
from zoneinfo import ZoneInfo

from nekomeeta.input_provider.context import NekonataContext

from handler.feature.mixer import FFmpegMixer
from handler.feature.path_builder import PathBuilder
from types_ import Attendees

_TZ = ZoneInfo("Asia/Tokyo")

logger = getLogger(__name__)


class AttendeesHandler:
    """
    Attendeesのデータをもとに副作用するクラス
    """

    def __init__(self, attendees: Attendees, dir: Path, encoding: str):
        self.attendees = attendees
        session_root = dir / datetime.now().strftime("%Y%m%d_%H%M%S")
        self.path_builder = PathBuilder(session_root, encoding)
        self.mixer = FFmpegMixer()

        logger.info(
            f"AttendeesHandler initialized with {len(attendees)} attendees, "
            f"session root: {session_root}, encoding: {encoding}"
        )

    def save_all_audio(self) -> list[Path]:
        output_files: list[Path] = []

        for user_id, data in self.attendees.items():
            file_path = self.path_builder.user_audio(user_id)
            data.format(file_path)
            output_files.append(file_path)

        return output_files

    def save_context(self) -> str:
        context = self._get_context()
        context_file = self.path_builder.context()

        with context_file.open("w", encoding="utf-8") as f:
            f.write(context)

        return context

    def mix(self, files: list[Path]) -> Path:
        output_file = self.path_builder.mixed_audio()
        self.mixer.mix(files, output_file)
        return output_file

    def get_attendees_ids_string(self) -> str:
        if not self.attendees:
            return "参加者がいません。"
        return "\n".join(f"- `{user_id}`" for user_id in self.attendees.keys())

    def _get_context(self) -> str:
        participant_names = ",".join(
            [
                NekonataContext.id2name.get(str(id), f"<@{id}>")
                for id in self.attendees.keys()
            ]
        )
        today_str = datetime.now(_TZ).strftime("%Y年%m月%d日")
        return f"録音日: {today_str}\n参加者: {participant_names}\n補足: {NekonataContext.note}"
