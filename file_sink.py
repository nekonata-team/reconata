import os
import tempfile

import discord
from discord.types.snowflake import Snowflake

_TMP_DIR = "tmp"


class FileSink(discord.sinks.Sink):
    def write(self, data: bytes, user: Snowflake) -> None:
        if user not in self.audio_data:
            os.makedirs(_TMP_DIR, exist_ok=True)
            temp = tempfile.NamedTemporaryFile(
                mode="w+b",
                delete=False,
                dir=_TMP_DIR,
                prefix=f"{user}_",
            )
            self.audio_data[user] = temp

        self.audio_data[user].write(data)

    def cleanup(self):
        for user, file in self.audio_data.items():
            file.close()
            self.audio_data[user] = file.name
