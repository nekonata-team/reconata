import subprocess
from pathlib import Path

from .mixer import Mixer, MixerError, NoAudioToMixError


class FFmpegNotFoundError(MixerError):
    """FFmpeg実行ファイルが見つからない場合のエラー。"""

    pass


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
