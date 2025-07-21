import os
import subprocess
from dataclasses import dataclass
from logging import getLogger
from pathlib import Path

logger = getLogger(__name__)


@dataclass
class AttendeeData:
    """
    FileSinkのaudio_dataを管理するクラス
    """

    temp_file_path: str

    def convert(self, output_path: Path):
        """
        ffmpegを使用して音声ファイルを変換します
        この関数は副作用をします
        output_pathに変換後のファイルを保存し、self.temp_file_pathのファイルを削除します
        """

        output_path.parent.mkdir(parents=True, exist_ok=True)
        command = [
            "ffmpeg",
            "-f",
            "s16le",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-i",
            self.temp_file_path,
            str(output_path),
        ]
        try:
            subprocess.run(command, check=True, capture_output=True, text=True)
            self._delete_temp_file()
        except FileNotFoundError:
            logger.error("FFmpeg is not installed or not found in PATH.")
            raise
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to convert: {e}")
            raise

    def _delete_temp_file(self):
        try:
            os.remove(self.temp_file_path)
        except OSError as e:
            logger.error(f"Error deleting temporary file {self.temp_file_path}: {e}")


Attendees = dict[int, AttendeeData]
