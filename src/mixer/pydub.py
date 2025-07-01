from pathlib import Path

from .mixer import Mixer, NoAudioToMixError


class PydubMixer(Mixer):
    """pydubライブラリを使用して音声をミックスするクラス。"""

    def _mix_internal(self, input_files: list[Path], output_file: Path):
        try:
            from pydub import AudioSegment  # type: ignore
        except ImportError:
            raise ImportError(
                "PydubMixerを使用するには 'pydub' をインストールしてください。"
            )

        segments = [
            AudioSegment.from_file(file) for file in input_files if file.is_file()
        ]

        if not segments:
            raise NoAudioToMixError("有効な音声ファイルが見つかりませんでした。")

        segments.sort(key=lambda seg: seg.duration_seconds, reverse=True)

        mixed = segments[0]
        for seg in segments[1:]:
            mixed = mixed.overlay(seg)

        mixed.export(output_file)
