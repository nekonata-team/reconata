import subprocess
from abc import ABC, abstractmethod
from pathlib import Path


class MixerError(Exception):
    """ミキサー処理中に発生したエラーの基底クラス。"""

    pass


class NoAudioToMixError(MixerError):
    """ミックス対象の有効な音声ファイルが見つからない場合のエラー。"""

    pass


class FFmpegNotFoundError(MixerError):
    """FFmpeg実行ファイルが見つからない場合のエラー。"""

    pass


class Mixer(ABC):
    """音声ファイルをミックスするための抽象基底クラス。"""

    def mix(self, input_files: list[Path], output_file: Path):
        """
        複数の入力音声ファイルを1つの出力ファイルにミックスする。

        Args:
            input_files: ミックスする音声ファイルのPathオブジェクトのリスト。
            output_file: 出力ファイルのPathオブジェクト。
        """
        if not input_files:
            raise NoAudioToMixError("ミックスする音声ファイルが指定されていません。")

        self._mix_internal(input_files, output_file)

    @abstractmethod
    def _mix_internal(self, input_files: list[Path], output_file: Path):
        """具象クラスで実装される実際のミックス処理。"""
        pass


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


class FFmpegMixer(Mixer):
    """FFmpegを使用して音声をミックスするクラス。"""

    def _mix_internal(self, input_files: list[Path], output_file: Path):
        valid_files = [f for f in input_files if f.is_file()]
        if not valid_files:
            raise NoAudioToMixError("有効な音声ファイルが見つかりませんでした。")

        command = ["ffmpeg"]
        for f in valid_files:
            command.extend(["-i", str(f)])

        num_inputs = len(valid_files)
        filter_streams = "".join(f"[{i}:a]" for i in range(num_inputs))
        filter_complex = f"{filter_streams}amix=inputs={num_inputs}:duration=longest,dynaudnorm[aout]"

        command.extend(
            [
                "-filter_complex",
                filter_complex,
                "-map",
                "[aout]",
                "-q:a",
                "0",
                "-y",
                str(output_file),
            ]
        )

        try:
            subprocess.run(
                command, check=True, capture_output=True, text=True, encoding="utf-8"
            )
        except FileNotFoundError as e:
            raise FFmpegNotFoundError(
                "ffmpegが見つかりません。パスを確認するか、インストールしてください。"
            ) from e
        except subprocess.CalledProcessError as e:
            error_message = (
                f"ffmpegの実行に失敗しました。\n"
                f"Return Code: {e.returncode}\n"
                f"Stderr: {e.stderr.strip()}"
            )
            raise MixerError(error_message) from e
