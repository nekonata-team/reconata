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
    # 必要に応じて他のプロンプトキーを追加
    # MEETING = "meeting"
    # INTERVIEW = "interview"


class ViewType(str, Enum):
    """Viewタイプ"""

    COMMIT = "commit"
    EDIT = "edit"
    # 将来的に他のViewタイプを追加可能
    # ADVANCED = "advanced"
    # CUSTOM = "custom"
