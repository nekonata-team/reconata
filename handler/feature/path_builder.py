from pathlib import Path


class PathBuilder:
    def __init__(self, dir: Path, encoding: str):
        self.dir = dir
        self.encoding = encoding

        dir.mkdir(parents=True, exist_ok=True)

    def user_audio(self, user_id: int) -> Path:
        return self.dir / f"{user_id}.{self.encoding}"

    def mixed_audio(self) -> Path:
        return self.dir / f"mixed.{self.encoding}"

    def user_id_from(self, path: Path) -> int:
        try:
            return int(path.stem)
        except Exception:
            raise ValueError(f"Invalid audio file name: {path.name}")

    def summary(self) -> Path:
        return self.dir / "summary.md"

    def transcription(self) -> Path:
        return self.dir / "transcription.txt"
