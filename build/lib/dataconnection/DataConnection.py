import logging
from enum import Enum
from typing import Any, Callable, Dict, Union
from src.base_connection import BaseConnection
from src.negotiator import Negotiator
from src.utils import random_token

logger = logging.getLogger(__name__)

class ConnectionType(Enum):
    DATA = "data"

class ServerMessageType(Enum):
    ANSWER = "answer"
    CANDIDATE = "candidate"

class DataConnectionErrorType(Enum):
    NOT_OPEN_YET = "not_open_yet"

class DataConnection(BaseConnection):
    ID_PREFIX = "dc_"
    MAX_BUFFERED_AMOUNT = 8 * 1024 * 1024

    def __init__(self, peer_id: str, provider: Any, options: Dict[str, Any]):
        super().__init__(peer_id, provider, options)
        self.connection_id = options.get('connection_id') or f"{self.ID_PREFIX}{random_token()}"
        self.label = options.get('label') or self.connection_id
        self.reliable = bool(options.get('reliable'))
        self._negotiator = Negotiator()
        self._open = False
        self.data_channel = None

        self._negotiator.start_connection(
            options.get('_payload') or {
                'originator': True,
                'reliable': self.reliable
            }
        )

    @property
    def type(self):
        return ConnectionType.DATA

    def _initialize_data_channel(self, dc):
        self.data_channel = dc
        
        def on_open():
            logger.info(f"DC#{self.connection_id} dc connection success")
            self._open = True
            self.emit("open")

        def on_message(e):
            logger.info(f"DC#{self.connection_id} dc onmessage: {e.data}")
            # self._handle_data_message(e)

        def on_close():
            logger.info(f"DC#{self.connection_id} dc closed for: {self.peer}")
            self.close()

        self.data_channel.on_open = on_open
        self.data_channel.on_message = on_message
        self.data_channel.on_close = on_close

    def close(self, options: Dict[str, bool] = None):
        if options and options.get('flush'):
            self.send({
                "__peerData": {
                    "type": "close"
                }
            })
            return

        if self._negotiator:
            self._negotiator.cleanup()
            self._negotiator = None

        if self.provider:
            self.provider._remove_connection(self)
            self.provider = None

        if self.data_channel:
            self.data_channel.on_open = None
            self.data_channel.on_message = None
            self.data_channel.on_close = None
            self.data_channel = None

        if not self._open:
            return

        self._open = False
        super().emit("close")

    def send(self, data: Any, chunked: bool = False):
        if not self._open:
            self.emit_error(
                DataConnectionErrorType.NOT_OPEN_YET,
                "Connection is not open. You should listen for the `open` event before sending messages."
            )
            return
        return self._send(data, chunked)

    def _send(self, data: Any, chunked: bool):
        # This method should be implemented in a subclass
        raise NotImplementedError("_send method must be implemented in a subclass")

    async def handle_message(self, message: Dict[str, Any]):
        payload = message['payload']

        if message['type'] == ServerMessageType.ANSWER:
            await self._negotiator.handle_sdp(message['type'], payload['sdp'])
        elif message['type'] == ServerMessageType.CANDIDATE:
            await self._negotiator.handle_candidate(payload['candidate'])
        else:
            logger.warning(f"Unrecognized message type: {message['type']} from peer: {self.peer}")
