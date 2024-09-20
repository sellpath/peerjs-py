import asyncio
from enum import Enum
from typing import Optional, Callable
# from peerjs_py.util import util
from peerjs_py.logger import logger
from peerjs_py.negotiator import Negotiator
from peerjs_py.base_connection import BaseConnection
from peerjs_py.enums import ConnectionType, ServerMessageType, ConnectionEventType
from peerjs_py.utils.random_token import random_token

class MediaConnectionEvents(BaseConnection.Events):
    stream: Callable[[object], None] #Emitted when a connection to the PeerServer is established.
    willCloseOnRemote: Callable[[], None] #Emitted when the auxiliary data channel is established.

class MediaConnection(BaseConnection):
    ID_PREFIX = "mc_"

    def __init__(self, peer_id: str, provider, options):
        super().__init__(peer_id, provider, options)
        self.label: str
        self._negotiator: Negotiator
        self._local_stream: Optional[object] = options.get('_stream')
        self._remote_stream: Optional[object] = None
        self.connection_id = options.get('connectionId') or self.ID_PREFIX + random_token()
        self._negotiator = Negotiator(self)

    async def initialize(self):
        if self._local_stream:
            await self._negotiator.start_connection({
                '_stream': self._local_stream,
                'originator': True
            })

    @property
    def type(self) -> ConnectionType:
        return ConnectionType.Media

    @property
    def local_stream(self) -> Optional[object]:
        return self._local_stream

    @property
    def remote_stream(self) -> Optional[object]:
        return self._remote_stream

    async def _initialize_data_channel(self, dc) -> None:
        self.data_channel = dc

        @self.data_channel.on("open")
        def on_open():
            logger.info(f"DC#{self.connection_id} dc connection success")
            self.emit("willCloseOnRemote")

        @self.data_channel.on("close")
        async def on_close():
            logger.info(f"DC#{self.connection_id} dc closed for: {self.peer}")
            await self.close()

    def add_stream(self, remote_stream: object) -> None:
        logger.info("Receiving stream", remote_stream)
        self._remote_stream = remote_stream
        super().emit("stream", remote_stream)

    async def handle_message(self, message: dict) -> None:
        message_type = message['type']
        payload = message['payload']

        if message_type == ServerMessageType.Answer:
            self._negotiator.handle_sdp(message_type, payload['sdp'])
            self._open = True
        elif message_type == ServerMessageType.Candidate:
            self._negotiator.handle_candidate(payload['candidate'])
        else:
            logger.warning(f"mediaconnection Unrecognized message type:{message_type} from peer:{self.peer}")

    async def answer(self, stream: Optional[object] = None, options: dict = {}) -> None:
        if self._local_stream:
            logger.warning("Local stream already exists on this MediaConnection. Are you answering a call twice?")
            return

        self._local_stream = stream

        if options.get('sdpTransform'):
            self.options['sdpTransform'] = options['sdpTransform']

        self._negotiator.start_connection({
            **self.options.get('_payload', {}),
            '_stream': stream
        })
        messages = self.provider._get_messages(self.connection_id)
        logger.debug(f"self.connection_id: {self.connection_id}  len(messages) : { len(messages)}")
        for msg in messages:
            await self.handle_message(msg)

        self._open = True

    async def close(self) -> None:
        if self._negotiator:
            await self._negotiator.cleanup()
            self._negotiator = None

        self._local_stream = None
        self._remote_stream = None

        if self.provider: # peer
            await self.provider._remove_connection(self)
            self.provider = None

        if self.options and self.options.get('_stream'):
            self.options['_stream'] = None

        if not self.open:
            return

        self._open = False
        super().emit("close")