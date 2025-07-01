from abc import ABC, abstractmethod
from pathlib import Path


class MixerError(Exception):
    """ミキサー処理中に発生したエラーの基底クラス。"""

    pass


class NoAudioToMixError(MixerError):
    """ミックス対象の有効な音声ファイルが見つからない場合のエラー。"""

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
