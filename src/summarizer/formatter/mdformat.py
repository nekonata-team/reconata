import mdformat

from .summary_formatter import SummaryFormatter


class MdFormatSummaryFormatter(SummaryFormatter):
    def format(self, summary: str) -> str:
        return mdformat.text(summary)
