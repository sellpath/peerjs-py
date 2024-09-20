import asyncio
from peerjs_py.binarypack.binarypack import Unpacker, Packer
from peerjs_py.dataconnection.StreamConnection.StreamConnection import StreamConnection
from peerjs_py.enums import ConnectionEventType

class MsgPack(StreamConnection):
    serialization = "MsgPack"

    def __init__(self, peer_id, provider, options):
        super().__init__(peer_id, provider, options)
        self._encoder = Packer()
        asyncio.create_task(self._read_stream())

    async def _read_stream(self):
        unpacker = Unpacker()
        while True:
            chunk = await self._raw_read_stream.read()
            if not chunk:
                break
            unpacker.feed(chunk)
            for msg in unpacker:
                if isinstance(msg, dict) and msg.get('__peerData', {}).get('type') == 'close':
                    self.close()
                    return
                self.emit(ConnectionEventType.Data.value, msg)

    def _send(self, data):
        return self.writer.write(self._encoder.pack(data))