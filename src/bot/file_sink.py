import os
import tempfile
from logging import getLogger

import discord
from discord.types.snowflake import Snowflake

_TMP_DIR = "tmp"

logger = getLogger(__name__)


class FileSink(discord.sinks.Sink):
    def __init__(self, *, filters=None):
        super().__init__(filters=filters)
        os.makedirs(_TMP_DIR, exist_ok=True)

    def write(self, data: bytes, user: Snowflake) -> None:
        logger.debug(f"Received audio data for user {user}, size: {len(data)} bytes")

        if user not in self.audio_data:
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
