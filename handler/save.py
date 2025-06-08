from pathlib import Path
from typing import Iterator

from handler.feature.attendees_handler import AttendeesHandler
from handler.handler import (
    AUDIO_NOT_RECORDED,
    AudioHandler,
)
from types_ import Attendees, MessageData, SendData


class SaveToFolderAudioHandler(AudioHandler):
    def __init__(self, dir: Path):
        self.dir = dir

    def __call__(self, attendees: Attendees) -> Iterator[MessageData]:
        if not attendees:
            yield SendData(content=AUDIO_NOT_RECORDED)
            return

        handler = AttendeesHandler(attendees, self.dir, self.encoding)
        handler.save_all()

        content = f"録音ファイルの保存が完了しました。\n\n参加者:\n{handler.get_attendees_ids_string()}"
        yield SendData(content=content)
