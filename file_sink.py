import os
import tempfile

import discord
from discord.sinks import AudioData
from discord.types.snowflake import Snowflake

_TMP_DIR = "tmp"


class FileSink(discord.sinks.MP3Sink):
    def write(self, data: bytes, user: Snowflake) -> None:
        if user not in self.audio_data:
            os.makedirs(_TMP_DIR, exist_ok=True)
            temp = tempfile.NamedTemporaryFile(
                mode="w+b",
                delete=True,
                dir=_TMP_DIR,
                prefix=f"{user}_",
            )
            self.audio_data[user] = AudioData(temp)

        self.audio_data[user].write(data)
        self.audio_data[user].file.flush()

    def remove_temp_files(self) -> None:
        for user, audio in self.audio_data.items():
            audio.file.close()
