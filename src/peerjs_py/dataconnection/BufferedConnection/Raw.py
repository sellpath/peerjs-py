from enum import Enum
from peerjs_py.dataconnection.BufferedConnection.BufferedConnection import BufferedConnection
from peerjs_py.enums import SerializationType, ConnectionEventType

class Raw(BufferedConnection):
    serialization = SerializationType.Raw
        
    async def _handle_data_message(self, data):
        super().emit(ConnectionEventType.Data.value, data)

    async def _send(self, data, _chunked):
        if self.data_channel and self.data_channel.readyState == "open":
            self.data_channel.send(data)
        else:
            await self._buffered_send(data)