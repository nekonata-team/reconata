import subprocess
from dataclasses import dataclass
from logging import getLogger
from pathlib import Path

logger = getLogger(__name__)


@dataclass
class AttendeeData:
    raw_file: str

    def format(self, output_path: Path):
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
            self.raw_file,
            str(output_path),
        ]
        try:
            subprocess.run(command, check=True, capture_output=True, text=True)
        except FileNotFoundError:
            logger.error("FFmpeg is not installed or not found in PATH.")
            raise
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to convert: {e}")
            raise


Attendees = dict[int, AttendeeData]
