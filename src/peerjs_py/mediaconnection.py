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
        self.connection_id = options.get('connection_id') or self.ID_PREFIX + random_token()
        self.label: str
        self._local_stream: Optional[object] = options.get('_stream')
        self._remote_stream: Optional[object] = None
        self._negotiator = Negotiator(self)
        self._open = False
        self._initialize_future = asyncio.Future()
        self._provider = provider
        
        logger.info(f"MediaConnection created with ID: {self.connection_id} for peer: {peer_id}")
        logger.debug(f"MediaConnection options: {options}")
        
        if self._local_stream:
            logger.info(f"Local stream provided for MediaConnection: {self.connection_id}")
        else:
            logger.warning(f"No local stream provided for MediaConnection: {self.connection_id}")


    async def initialize(self):
        logger.info(f"Initializing MediaConnection: {self.connection_id}")
        try:
            if self._local_stream:
                logger.debug(f"Starting connection with local stream for MediaConnection: {self.connection_id}")
                await self._negotiator.start_connection({
                    '_stream': self._local_stream,
                    'originator': True
                })
                logger.info(f"Connection started for MediaConnection: {self.connection_id}")
            else:
                logger.warning(f"No local stream to initialize for MediaConnection: {self.connection_id}")            
        except Exception as e:
            logger.error(f"Error initializing MediaConnection {self.connection_id}: {str(e)}")
            self._initialize_future.set_exception(e)
        
        logger.info(f"MediaConnection initialization completed for: {self.connection_id}")

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
        if self.data_channel:
            logger.info(f"DC#{self.connection_id} Data channel already initialized")
            return
        
        logger.info(f"Initializing data channel for MediaConnection: {self.connection_id}")
        self.data_channel = dc

        @self.data_channel.on("open")
        async def on_open():
            logger.info(f"DC#{self.connection_id} dc connection success")
            self._open = True
            self.open_future.set_result(True)
            # self.emit(ConnectionEventType.Open.value)
            self.emit("willCloseOnRemote") # follow ts side impl

        @self.data_channel.on("close")
        async def on_close():
            logger.info(f"DC#{self.connection_id} dc closed for: {self.peer}")
            await self.close()

        @self.data_channel.on("message")
        async def on_message(msg):
            logger.info(f"DC#{self.connection_id} Received message on MediaConnection: {msg}")
            # Handle message if needed

        @self.data_channel.on("error")
        async def on_error(err):
            logger.error(f"DC#{self.connection_id} Data channel error on MediaConnection: {err}")

        logger.info(f"Data channel initialized for MediaConnection: {self.connection_id}")

    def add_stream(self, remote_stream: object) -> None:
        logger.info(f"Receiving stream for MediaConnection: {self.connection_id}")
        self._remote_stream = remote_stream
        super().emit("stream", remote_stream)

    async def handle_message(self, message: dict) -> None:
        message_type = message['type']
        payload = message['payload']

        logger.debug(f"Handling message for MediaConnection {self.connection_id}: {message_type}")

        if message_type == ServerMessageType.Answer:
            await self._negotiator.handle_sdp(message_type, payload['sdp'])
            # self._open = True
            # self.open_future.set_result(True)
            logger.info(f"MediaConnection {self.connection_id} is now open")
        elif message_type == ServerMessageType.Candidate:
            await self._negotiator.handle_candidate(payload['candidate'])
        elif message_type == ServerMessageType.Offer.value:
            await self._negotiator.handle_sdp(message_type, payload['sdp'])
        else:
            logger.warning(f"Unrecognized message type:{message_type} from peer:{self.peer} for MediaConnection: {self.connection_id}")

    async def answer(self, stream: Optional[object] = None, options: dict = {}) -> None:
        logger.info(f"Answering call for MediaConnection: {self.connection_id}")
        if self._local_stream:
            logger.warning(f"Local stream already exists on MediaConnection: {self.connection_id}. Are you answering a call twice?")
            return

        self._local_stream = stream

        if options.get('sdpTransform'):
            self.options['sdpTransform'] = options['sdpTransform']

        await self._negotiator.start_connection({
            **self.options.get('_payload', {}),
            '_stream': stream
        })
        messages = self.provider._get_messages(self.connection_id)
        logger.debug(f"Processing {len(messages)} queued messages for MediaConnection: {self.connection_id}")
        for msg in messages:
            await self.handle_message(msg)

        self._open = True
        self.open_future.set_result(True)
        logger.info(f"MediaConnection {self.connection_id} answered and open")

    async def close(self) -> None:
        logger.info(f"Closing MediaConnection: {self.connection_id}")
        if self._negotiator:
            await self._negotiator.cleanup()
            self._negotiator = None

        self._local_stream = None
        self._remote_stream = None

        if self.provider:
            await self.provider._remove_connection(self)
            self.provider = None

        if self.options and self.options.get('_stream'):
            self.options['_stream'] = None

        if not self.open:
            logger.info(f"MediaConnection {self.connection_id} was already closed")
            return

        self._open = False
        self.open_future.set_result(False)
        super().emit("close")
        logger.info(f"MediaConnection {self.connection_id} closed")