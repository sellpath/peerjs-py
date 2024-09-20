import asyncio
from peerjs_py.logger import logger
from abc import ABC, abstractmethod
from typing import Any

class StreamConnection(ABC):
    MAX_BUFFERED_AMOUNT = 16384

    def __init__(self, peer_id: str, provider: Any, options: dict):
        self._CHUNK_SIZE = 1024 * 8 * 4
        self.peer_id = peer_id
        self.provider = provider
        self.options = {**options, "reliable": True}
        self.data_channel = None
        self.connection_id = None
        self.logger = logger.getLogger(__name__)
        self._split_stream = None
        self._raw_send_stream = None
        self._raw_read_stream = None

    async def _initialize_data_channel(self, dc):
        self.data_channel = dc
        self.data_channel.binaryType = "arraybuffer"
        self.data_channel.bufferedAmountLowThreshold = self.MAX_BUFFERED_AMOUNT // 2
        
        self._split_stream = asyncio.StreamReader()
        self._raw_send_stream = asyncio.StreamWriter(self.data_channel, None, None, None)
        self._raw_read_stream = asyncio.StreamReader()
        
        self.data_channel.on_message = self._on_message
        self.data_channel.on_bufferedamountlow = self._on_bufferedamountlow

    async def _split_stream_transform(self, reader, writer):
        while True:
            chunk = await reader.read(self._CHUNK_SIZE)
            if not chunk:
                break
            await writer.write(chunk)
            await writer.drain()

    async def _raw_send_stream_transform(self, reader, writer):
        while True:
            chunk = await reader.read(self._CHUNK_SIZE)
            if not chunk:
                break
            while self.data_channel.bufferedAmount > self.MAX_BUFFERED_AMOUNT - len(chunk):
                await self._wait_for_buffer_low()
            try:
                self.data_channel.send(chunk)
            except Exception as e:
                self.logger.error(f"DC#{self.connection_id} Error when sending:", exc_info=e)
                self.close()
                raise

    async def _wait_for_buffer_low(self):
        low_event = asyncio.Event()
        self.data_channel.on_bufferedamountlow = lambda: low_event.set()
        await low_event.wait()

    async def write(self, data: bytes):
        self._split_stream.feed_data(data)
        await self._split_stream_transform(self._split_stream, self._raw_send_stream)

    async def _raw_read_stream_transform(self, reader, writer):
        while True:
            chunk = await reader.read(self._CHUNK_SIZE)
            if not chunk:
                break
            writer.write(chunk)
            await writer.drain()

    def _on_message(self, message):
        self._raw_read_stream.feed_data(message.data)

    def _on_bufferedamountlow(self):
        pass  # This method can be used to implement flow control if needed

    @abstractmethod
    def close(self):
        pass

    async def start_streaming(self):
        # Start the stream transformations
        asyncio.create_task(self._split_stream_transform(self._split_stream, self._raw_send_stream))
        asyncio.create_task(self._raw_send_stream_transform(self._raw_send_stream, None))
        asyncio.create_task(self._raw_read_stream_transform(self._raw_read_stream, None))