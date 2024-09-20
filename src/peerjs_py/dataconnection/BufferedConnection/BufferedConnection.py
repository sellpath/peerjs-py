from peerjs_py.logger import logger
from peerjs_py.dataconnection.DataConnection import DataConnection

class BufferedConnection(DataConnection):
    def __init__(self, peer_id, provider, options):
        super().__init__(peer_id, provider, options)
        self._buffer = []
        self._buffer_size = 0
        self._buffering = False

    @property
    def buffer_size(self):
        return self._buffer_size

    async def _initialize_data_channel(self, dc):
        await super()._initialize_data_channel(dc)
        self.data_channel.binaryType = "arraybuffer"
        self.data_channel.on("message", self._handle_data_message)

    async def _handle_data_message(self, e):
        # This method should be implemented in subclasses
        raise NotImplementedError("_handle_data_message must be implemented in subclasses")

    # _send for buffered case
    async def _buffered_send(self, msg):
        if self._buffering or not await self._try_send(msg):
            self._buffer.append(msg)
            self._buffer_size = len(self._buffer)

    async def _try_send(self, msg):
        if not self.open:
            return False

        if self.data_channel.bufferedAmount > DataConnection.MAX_BUFFERED_AMOUNT:
            self._buffering = True
            # Note: In Python, we'd typically use a threading.Timer or asyncio for this
            # For simplicity, we'll use a basic approach here
            self._buffering = False
            await self._try_buffer()
            return False

        try:
            self.data_channel.send(msg)
        except Exception as e:
            logger.error(f"DC#{self.connection_id} Error when sending: {e}")
            self._buffering = True
            await self.close()
            return False

        return True

    async def _try_buffer(self):
        if not self.open or not self._buffer:
            return

        msg = self._buffer[0]

        if await self._try_send(msg):
            self._buffer.pop(0)
            self._buffer_size = len(self._buffer)
            await self._try_buffer()

    async def close(self, options=None):
        if options and options.get('flush'):
            self.send({
                "__peerData": {
                    "type": "close"
                }
            })
            return

        self._buffer = []
        self._buffer_size = 0
        await super().close()