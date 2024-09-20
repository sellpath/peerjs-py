from peerjs_py.dataconnection.BufferedConnection.BufferedConnection import BufferedConnection
from peerjs_py.enums import SerializationType, DataConnectionErrorType, EnumAwareJSONEncoder, ConnectionEventType
# from peerjs_py.util import util
import json
from peerjs_py.logger import logger

from typing import Any, Callable, Dict, Union

CHUNKED_MTU = 16300
class Json(BufferedConnection):
    serialization = SerializationType.JSON

    def __init__(self, peer_id: str, provider, options):
        super().__init__(peer_id, provider, options)
        self.encoder = lambda s: s.encode('utf-8')
        self.decoder = lambda b: b.decode('utf-8')
        
        # self.stringify = json.dumps
        self.stringify = lambda obj: json.dumps(obj, cls=EnumAwareJSONEncoder)
        self.parse = json.loads

    async def _handle_data_message(self, data: bytes):
        if isinstance(data, str):
            try:
                deserialized_data = self.parse(data.strip('"'))
            except json.JSONDecodeError:
                # If it's not valid JSON, treat it as a plain string
                deserialized_data = data.strip('"')
        else:
            deserialized_data = self.parse(self.decoder(data))

        try:
        # PeerJS specific message
            peer_data = deserialized_data.get("__peerData")
            if peer_data and peer_data.get("type") == "close":
                await self.close()
                return
        except:
            # logger.error(f"_handle_data_message  no __peerData error: {deserialized_data}")
            pass
        # self.emit(ConnectionEventType.Data.value, deserialized_data)
        self.emit(ConnectionEventType.Data.value, deserialized_data)

    async def _send(self, data, _chunked):
        encoded_data = self.encoder(self.stringify(data))
        if len(encoded_data) >= CHUNKED_MTU:
            self.emit_error(
                DataConnectionErrorType.MessageToBig.value,
                "Message too big for JSON channel"
            )
            return
        if self.data_channel and self.data_channel.readyState == "open":
            self.data_channel.send(encoded_data)
        else:
            await self._buffered_send(encoded_data)