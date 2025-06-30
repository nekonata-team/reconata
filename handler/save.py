import asyncio
from pathlib import Path

from types_ import Attendees, SendData

from .audio_handler import (
    AUDIO_NOT_RECORDED,
    AudioHandler,
    AudioHandlerResult,
)
from .feature.attendees_handler import AttendeesHandler


class SaveToFolderAudioHandler(AudioHandler):
    def __init__(self, dir: Path):
        self.dir = dir

    async def __call__(self, attendees: Attendees) -> AudioHandlerResult:
        if not attendees:
            yield SendData(content=AUDIO_NOT_RECORDED)
            return

        handler = AttendeesHandler(attendees, self.dir, self.encoding)
        await asyncio.to_thread(handler.save_all_audio)

        content = f"録音ファイルの保存が完了しました。\n\n参加者:\n{handler.get_attendees_ids_string()}"
        yield SendData(content=content)
