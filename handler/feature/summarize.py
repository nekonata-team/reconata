from pathlib import Path

from summarizer.summarizer import Summarizer


class MeetingSummarizer:
    def __init__(self, summarizer: Summarizer):
        self.summarizer = summarizer

    def __call__(self, transcription: str, output_file: Path | None = None):
        summary = self.summarizer.generate_meeting_notes(transcription)
        if output_file is not None:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(summary)
        return summary
