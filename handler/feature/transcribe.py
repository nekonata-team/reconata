from pathlib import Path

from transcriber.transcriber import Transcriber


class MeetingTranscriber:
    def __init__(self, transcriber: Transcriber):
        self.transcriber = transcriber

    def __call__(self, input_file: Path, output_file: Path | None) -> str:
        transcription = self.transcriber.transcribe(str(input_file))
        if output_file is not None:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(transcription)
        return transcription
