from pathlib import Path


class PathBuilder:
    def __init__(self, dir: Path, audio_encoding: str = "mp3"):
        self.dir = dir
        self.audio_encoding = audio_encoding

        dir.mkdir(parents=True, exist_ok=True)

    def user_audio(self, user_id: int) -> Path:
        return self.dir / f"{user_id}.{self.audio_encoding}"

    def mixed_audio(self) -> Path:
        return self.dir / f"mixed.{self.audio_encoding}"

    def context(self) -> Path:
        return self.dir / "context.txt"

    def user_id_from(self, path: Path) -> int:
        try:
            return int(path.stem)
        except Exception:
            raise ValueError(f"Invalid audio file name: {path.name}")

    def summary(self) -> Path:
        return self.dir / "summary.md"

    def transcription(self) -> Path:
        return self.dir / "transcription.txt"
