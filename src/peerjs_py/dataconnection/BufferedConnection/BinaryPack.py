import asyncio

from peerjs_py.enums import SerializationType, ConnectionEventType
from peerjs_py.logger import logger
from peerjs_py.binarypack.binarypack import pack, unpack
from peerjs_py.dataconnection.BufferedConnection.BufferedConnection import BufferedConnection
from peerjs_py.dataconnection.BufferedConnection.binaryPackChunker import BinaryPackChunker, concat_array_buffers

class BinaryPack(BufferedConnection):
    serialization = SerializationType.Binary

    def __init__(self, peer_id, provider, options):
        super().__init__(peer_id, provider, options)
        self.chunker = BinaryPackChunker()
        # self.serialization = SerializationType.Binary
        self._chunked_data = {}

    async def close(self, options=None):
        await super().close(options)
        self._chunked_data = {}

    async def _handle_data_message(self, data):
        deserialized_data = unpack(data)

        peer_data = deserialized_data.get("__peerData")
        if peer_data:
            if peer_data.get("type") == "close":
                await self.close()
                return

            self._handle_chunk(deserialized_data)
            return

        # self.emit(ConnectionEventType.Data.value, deserialized_data)
        self.emit(ConnectionEventType.Data.value, deserialized_data)

    def _handle_chunk(self, data):
        chunk_id = data["__peerData"]
        chunk_info = self._chunked_data.get(chunk_id, {
            "data": [],
            "count": 0,
            "total": data["total"]
        })

        chunk_info["data"][data["n"]] = bytes(data["data"])
        chunk_info["count"] += 1
        self._chunked_data[chunk_id] = chunk_info

        if chunk_info["total"] == chunk_info["count"]:
            del self._chunked_data[chunk_id]
            complete_data = concat_array_buffers(chunk_info["data"])
            self._handle_data_message({"data": complete_data})

    async def _send(self, data, chunked):
        blob = pack(data)
        if isinstance(blob,  asyncio.Future):
            return self._send_blob(blob)

        if not chunked and len(blob) > self.chunker.chunked_mtu:
            await self._send_chunks(blob)
            return

        if self.data_channel and self.data_channel.readyState == "open":
            self.data_channel.send(data)
        else:
            await self._buffered_send(data)

    async def _send_blob(self, blob_promise: asyncio.Future):
        blob = await blob_promise
        if len(blob) > self.chunker.chunked_mtu:
            await self._send_chunks(blob)
            return

        await self._buffered_send(blob)

    async def _send_chunks(self, blob):
        blobs = self.chunker.chunk(blob)
        logger.debug(f"DC#{self.connection_id} Try to send {len(blobs)} chunks...")

        for blob in blobs:
            await self.send(blob, True)