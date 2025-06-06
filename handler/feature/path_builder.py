from datetime import datetime
from pathlib import Path


class PathBuilder:
    def user_audio(self, folder: Path, user_id: int, ext: str) -> Path:
        return folder / f"{user_id}.{ext}"

    def mixed_audio(self, folder: Path, ext: str) -> Path:
        return folder / f"mixed.{ext}"

    def session_root(self, base_folder: Path, dt: datetime | None = None) -> Path:
        if dt is None:
            dt = datetime.now()
        return base_folder / dt.strftime("%Y%m%d_%H%M%S")

    def user_id_from(self, path: Path) -> int:
        try:
            return int(path.stem)
        except Exception:
            raise ValueError(f"Invalid audio file name: {path.name}")
