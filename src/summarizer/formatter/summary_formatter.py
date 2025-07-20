from abc import ABC, abstractmethod


class SummaryFormatter(ABC):
    """
    議事録などをフォーマットするための抽象クラス
    """

    @abstractmethod
    def format(self, summary: str) -> str:
        pass
