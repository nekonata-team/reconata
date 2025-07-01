from datetime import datetime
from logging import getLogger
from pathlib import Path

from src.bot.attendee import Attendees
from src.mixer.ffmpeg import FFmpegMixer

from .path_builder import PathBuilder

logger = getLogger(__name__)


def create_path_builder(dir: Path) -> PathBuilder:
    session_root = dir / datetime.now().strftime("%Y%m%d_%H%M%S")
    return PathBuilder(session_root)


def mix(files: list[Path], output_file: Path) -> Path:
    mixer = FFmpegMixer()
    mixer.mix(files, output_file)
    return output_file


def save_all_audio(path_builder: PathBuilder, attendees: Attendees) -> list[Path]:
    output_files: list[Path] = []

    for user_id, data in attendees.items():
        file_path = path_builder.user_audio(user_id)
        data.format(file_path)
        output_files.append(file_path)

    return output_files


def get_attendees_ids_string(attendees: Attendees) -> str:
    if not attendees:
        return "参加者がいません。"
    return "\n".join(f"- `{user_id}`" for user_id in attendees.keys())
