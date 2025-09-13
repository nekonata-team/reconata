import os
import random
import tempfile
import time
from logging import getLogger
from typing import Literal

from openai import OpenAI
from pydub import AudioSegment
from pydub.utils import make_chunks

from .transcriber import IterableTranscriber, Segment

OpenAIWhisperModel = Literal["gpt-4o-transcribe", "gpt-4o-mini-transcribe"]

logger = getLogger(__name__)


class OpenAIWhisperTranscriber(IterableTranscriber):
    """OpenAI Whisper を利用して音声をテキスト化する実装クラス"""

    def __init__(
        self,
        api_key: str,
        model: OpenAIWhisperModel = "gpt-4o-transcribe",
    ):
        self.model = model
        self._model = OpenAI(api_key=api_key)

    async def transcribe_iter(self, audio_path: str):
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"音声ファイルが見つかりません: {audio_path}")
        try:
            audio = AudioSegment.from_file(audio_path)
            chunk_seconds = 5 * 60
            chunks = make_chunks(
                audio,
                chunk_seconds * 1000,
            )

            for idx, chunk in enumerate(chunks, start=1):
                logger.info(f"Processing chunk {idx}/{len(chunks)}...")

                with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                    chunk.export(tmp.name, format="mp3")
                    tmp_path = tmp.name
                    text = self._transcribe_with_retry(tmp_path)

                    yield Segment(
                        start=(idx - 1) * chunk_seconds,
                        end=min(idx * chunk_seconds, len(audio) / 1000),
                        text=text,
                    )

        except Exception as e:
            raise RuntimeError("音声のテキスト化に失敗しました") from e

    def _transcribe_with_retry(
        self,
        file_path: str,
        *,
        max_retries: int = 5,
        base_delay: float = 1.0,
    ) -> str:
        """Call transcription API with retries and exponential backoff.

        Returns the transcribed text on success, raises the last exception on failure.
        """
        attempt = 0
        while True:
            attempt += 1
            try:
                with open(file_path, "rb") as f:
                    resp = self._model.audio.transcriptions.create(
                        model=self.model,
                        file=f,
                        language="ja",
                    )
                return resp.text
            except Exception as e:  # Broad catch to be robust across SDK versions
                if attempt >= max_retries:
                    raise
                # Exponential backoff with jitter
                delay = base_delay * (2 ** (attempt - 1))
                delay = delay + random.uniform(0, 0.5)
                print(
                    f"  Error on attempt {attempt}/{max_retries}: {e}. Retrying in {delay:.1f}s..."
                )
                time.sleep(delay)
