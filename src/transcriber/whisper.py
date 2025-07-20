import os
from logging import getLogger
from typing import Literal

from .transcriber import Transcriber

# [openai/whisper: Robust Speech Recognition via Large-Scale Weak Supervision](https://github.com/openai/whisper?tab=readme-ov-file#available-models-and-languages)
WhisperModelSize = Literal[
    "tiny",
    "tiny.en",
    "base",
    "base.en",
    "small",
    "small.en",
    "medium",
    "medium.en",
    "large",
    "turbo",
]

logger = getLogger(__name__)


class WhisperTranscriber(Transcriber):
    """Whisper を利用して音声をテキスト化する実装クラス"""

    def __init__(
        self, model_size: WhisperModelSize = "small", beam_size: int = 1
    ) -> None:
        self.model_size = model_size
        self.beam_size = beam_size
        self._model = None

    def _get_model(self):
        if self._model is None:
            import whisper

            logger.info(
                f"Loading Whisper model: size='{self.model_size}', beam_size='{self.beam_size}'"
            )

            self._model = whisper.load_model(self.model_size)
        return self._model

    def transcribe(self, audio_path: str) -> str:
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"音声ファイルが見つかりません: {audio_path}")
        try:
            model = self._get_model()
            result = model.transcribe(
                audio_path, beam_size=self.beam_size, language="ja"
            )
            segments = result.get("segments", [])
            return "\n".join([segment["text"] for segment in segments])  # type: ignore
        except Exception as e:
            raise RuntimeError("音声のテキスト化に失敗しました") from e
