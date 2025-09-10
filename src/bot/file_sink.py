import asyncio
import os
import tempfile
import threading
import time
from concurrent.futures import Future
from logging import getLogger
from typing import IO

import discord
from discord.types.snowflake import Snowflake

_TMP_DIR = "tmp"

logger = getLogger(__name__)


class FileSink(discord.sinks.Sink):
    """
    音声データをノンブロッキングでキューに入れ、
    バックグラウンドの別スレッドでファイルに書き出す自己完結型シンク。
    """

    def __init__(self, loop: asyncio.AbstractEventLoop, *, filters=None):
        super().__init__(filters=filters)
        os.makedirs(_TMP_DIR, exist_ok=True)
        self.loop = loop

        self.audio_data: dict[Snowflake, str] = {}
        self._file_handles: dict[Snowflake, IO[bytes]] = {}
        self._file_lock = threading.Lock()  # ファイルハンドル作成の排他制御
        self._queue: asyncio.Queue[tuple[Snowflake, bytes] | None] = asyncio.Queue(
            maxsize=1000
        )
        self._writer_task: asyncio.Task | None = None
        self._writer_task_starter: Future | None = None
        self._is_closed = False

        self._bytes_total = 0
        self._last_packet = 0.0

    def write(self, data: bytes, user: Snowflake) -> None:
        """
        書き込みでブロックするとWebsocketのヘルスチェックが失敗する可能性があるため、
        非同期で書き込みを行う。具体的にはasyncio.Queueを用いてConsumerパターンを使用する
        音声データを受け取り、内部キューに配置する。
        このメソッドは別スレッドから同期的に呼ばれる。
        """
        if self._is_closed:
            logger.warning("FileSink is closed. Ignoring write request.")
            return

        self._ensure_writer_task_started()

        self._ensure_file_handle(user)

        self._bytes_total += len(data)
        self._last_packet = time.monotonic()

        # キューへのデータ追加（別スレッドからの呼び出しを考慮）
        try:
            if threading.current_thread() is threading.main_thread():
                self._queue.put_nowait((user, data))
            else:
                # イベントループスレッドでputする
                asyncio.run_coroutine_threadsafe(
                    self._queue.put((user, data)), self.loop
                )
        except asyncio.QueueFull:
            logger.warning(f"Audio queue is full. Discarding data for user {user}.")

    def metrics(self) -> dict:
        qsize = self._queue.qsize()
        return {
            "files": len(self.audio_data),
            "queue_size": qsize,
            "queue_max": self._queue.maxsize,
            "bytes_total": self._bytes_total,
            "last_packet": self._last_packet,
            "writer_state": (
                "none"
                if self._writer_task is None
                else (
                    "done"
                    if self._writer_task.done()
                    else ("cancelled" if self._writer_task.cancelled() else "running")
                )
            ),
            "closed": self._is_closed,
        }

    def _ensure_writer_task_started(self):
        """書き込みタスクの開始を保証する（スレッドセーフ）"""
        if self._writer_task is None and self._writer_task_starter is None:
            self._writer_task_starter = asyncio.run_coroutine_threadsafe(
                self._start_writer_once(),
                self.loop,
            )

    def _ensure_file_handle(self, user: Snowflake):
        """ユーザーのファイルハンドルの存在を保証する（スレッドセーフ）"""
        if user not in self._file_handles:
            with self._file_lock:
                # ダブルチェック: ロック取得後に再確認
                if user not in self._file_handles:
                    try:
                        temp_file = tempfile.NamedTemporaryFile(
                            mode="w+b",
                            delete=False,
                            dir=_TMP_DIR,
                            prefix=f"{user}_",
                            suffix=".pcm",
                        )
                        self._file_handles[user] = temp_file
                        self.audio_data[user] = temp_file.name
                        logger.info(
                            f"Created audio file for user {user}: {temp_file.name}"
                        )
                    except Exception as e:
                        logger.error(
                            f"Failed to create file handle for user {user}: {e}"
                        )
                        raise

    async def _start_writer_once(self):
        """一度だけ書き込みタスクを開始するコルーチン"""
        if self._writer_task is None:
            self._writer_task = asyncio.create_task(self._write_loop())
            logger.info("FileSink writer task has been created and started.")

    async def _write_loop(self):
        """メインの書き込みループ"""
        logger.info("Writer loop started.")

        try:
            while True:
                item = await self._queue.get()
                if item is None:
                    logger.info("Received shutdown signal.")
                    self._queue.task_done()
                    break

                user, data = item
                try:
                    await self._write_data_safely(user, data)
                except Exception as e:
                    logger.error(f"Error writing audio data for user {user}: {e}")
                finally:
                    self._queue.task_done()
        finally:
            # 必ずファイルハンドルを閉じる
            await self._close_all_file_handles()

    async def _write_data_safely(self, user: Snowflake, data: bytes):
        """安全にデータを書き込む"""
        fh = self._file_handles.get(user)
        if fh and not fh.closed:
            try:
                await asyncio.to_thread(fh.write, data)
                await asyncio.to_thread(fh.flush)  # 定期的にフラッシュ
            except Exception as e:
                logger.error(f"Failed to write data for user {user}: {e}")
                # ファイルハンドルが破損している可能性があるため削除
                with self._file_lock:
                    if user in self._file_handles:
                        try:
                            self._file_handles[user].close()
                        except Exception as e:
                            logger.error(
                                f"Error closing file handle for user {user}: {e}"
                            )
                        del self._file_handles[user]
                raise

    async def _close_all_file_handles(self):
        """すべてのファイルハンドルを安全に閉じる"""
        logger.info("Closing all file handles...")

        with self._file_lock:
            handles_to_close = list(self._file_handles.values())
            self._file_handles.clear()

        for fh in handles_to_close:
            try:
                if not fh.closed:
                    await asyncio.to_thread(fh.close)
            except Exception as e:
                logger.error(f"Error closing file handle: {e}")

        logger.info("All file handles closed.")

    async def close(self):
        """シンクを閉じる"""
        if self._is_closed:
            return

        self._is_closed = True
        logger.info("Closing FileSink...")

        # 書き込みタスクが存在し、まだ完了していない場合
        if self._writer_task and not self._writer_task.done():
            logger.info("Sending shutdown signal to writer task...")
            try:
                await self._queue.put(None)
                # タイムアウト付きで終了を待つ
                await asyncio.wait_for(self._writer_task, timeout=5.0)
                logger.info("Writer task completed successfully.")
            except asyncio.TimeoutError:
                logger.warning(
                    "Writer task did not complete within timeout. Cancelling..."
                )
                self._writer_task.cancel()
                try:
                    await self._writer_task
                except asyncio.CancelledError:
                    pass

        # 未完了のスターターFutureがあれば待つ
        if self._writer_task_starter and not self._writer_task_starter.done():
            try:
                await asyncio.wrap_future(self._writer_task_starter)
            except Exception as e:
                logger.error(f"Error waiting for writer task starter: {e}")

        logger.info("FileSink closed.")

    def cleanup(self):
        pass
