import os
from logging import getLogger
from typing import Literal, cast

from faster_whisper import BatchedInferencePipeline, WhisperModel

from .transcriber import IterableTranscriber, Segment, Transcriber

ComputeType = Literal["float16", "int8", "float16_int8"]
FasterWhisperModelSize = Literal[
    "tiny",
    "tiny.en",
    "base",
    "base.en",
    "small",
    "small.en",
    "distil-small.en",
    "medium",
    "medium.en",
    "distil-medium.en",
    "large-v1",
    "large-v2",
    "large-v3",
    "large",
    "distil-large-v2",
    "distil-large-v3",
    "large-v3-turbo",
    "turbo",
]

logger = getLogger(__name__)


class FasterWhisperTranscriber(Transcriber, IterableTranscriber):
    """faster-whisper を利用して音声をテキスト化する実装クラス"""

    def __init__(
        self,
        model_size: FasterWhisperModelSize = "small",
        compute_type: ComputeType = "int8",
        beam_size: int = 5,
        hotwords: str | None = None,
        batch_size: int | None = None,
    ):
        self.model_size = model_size
        self.compute_type = compute_type
        self.beam_size = beam_size
        self.hotwords = hotwords
        self.batch_size = batch_size
        self._model = None

    def _get_model(self) -> BatchedInferencePipeline | WhisperModel:
        if self._model is None:
            logger.info(
                f"Loading FasterWhisper model: size='{self.model_size}', compute_type='{self.compute_type}', beam_size='{self.beam_size}', hotwords='{self.hotwords}'"
            )

            self._model = WhisperModel(self.model_size, compute_type=self.compute_type)
            if self.batch_size is not None:
                self._model = BatchedInferencePipeline(model=self._model)

        return self._model

    def transcribe(self, audio_path: str) -> str:
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"音声ファイルが見つかりません: {audio_path}")
        try:
            segments, info = self._transcribe(audio_path)
            texts = [segment.text for segment in segments]
            return "\n".join(texts)
        except Exception as e:
            raise RuntimeError("音声のテキスト化に失敗しました") from e

    async def transcribe_iter(self, audio_path: str):
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"音声ファイルが見つかりません: {audio_path}")
        try:
            segments, info = self._transcribe(audio_path)
            for segment in segments:
                yield Segment(
                    start=segment.start,
                    end=segment.end,
                    text=segment.text,
                )
        except Exception as e:
            raise RuntimeError("音声のテキスト化に失敗しました") from e

    def _transcribe(self, audio_path: str):
        model = self._get_model()

        if isinstance(model, BatchedInferencePipeline):
            batch_size = cast(int, self.batch_size)
            return model.transcribe(
                audio_path,
                beam_size=self.beam_size,
                language="ja",
                hotwords=self.hotwords,
                batch_size=batch_size,
            )
        else:
            return model.transcribe(
                audio_path,
                beam_size=self.beam_size,
                language="ja",
                hotwords=self.hotwords,
            )
