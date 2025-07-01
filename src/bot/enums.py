from enum import Enum


class Mode(str, Enum):
    """録音モード"""

    MINUTE = "minute"
    TRANSCRIPTION = "transcription"
    SAVE = "save"


class PromptKey(str, Enum):
    """プロンプトキー"""

    DEFAULT = "default"
    OBSIDIAN = "obsidian"
