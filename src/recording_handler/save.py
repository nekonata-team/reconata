import asyncio
from pathlib import Path

from .attendee import Attendees
from .common import create_path_builder, get_attendees_ids_string, save_all_audio
from .message_data import SendData
from .recording_handler import (
    AUDIO_NOT_RECORDED,
    AudioHandlerResult,
    RecordingHandler,
)


class SaveToFolderRecordingHandler(RecordingHandler):
    def __init__(
        self,
        dir: Path = Path("./data"),
    ):
        self.dir = dir

    async def __call__(self, attendees: Attendees) -> AudioHandlerResult:
        if not attendees:
            yield SendData(content=AUDIO_NOT_RECORDED)
            return

        path_builder = create_path_builder(self.dir)
        await asyncio.to_thread(save_all_audio, path_builder, attendees)

        content = f"録音ファイルの保存が完了しました。\n\n参加者:\n{get_attendees_ids_string(attendees)}"
        yield SendData(content=content)
