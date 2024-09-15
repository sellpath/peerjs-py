from enum import Enum
from typing import Optional, Callable
from src.util import util
from src.logger import logger
from src.negotiator import Negotiator
from src.base_connection import BaseConnection
from src.enums import ConnectionType, ServerMessageType

class MediaConnectionEvents(BaseConnection.Events):
    stream: Callable[[object], None]
    willCloseOnRemote: Callable[[], None]

class MediaConnection(BaseConnection):
    ID_PREFIX = "mc_"

    def __init__(self, peer_id: str, provider: 'Peer', options: dict):
        super().__init__(peer_id, provider, options)
        self.label: str
        self._negotiator: Negotiator
        self._local_stream: Optional[object] = options.get('_stream')
        self._remote_stream: Optional[object] = None
        self.connection_id = options.get('connectionId') or self.ID_PREFIX + util.random_token()
        self._negotiator = Negotiator(self)

        if self._local_stream:
            self._negotiator.start_connection({
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

    def _initialize_data_channel(self, dc: object) -> None:
        self.data_channel = dc

        def on_open():
            logger.log(f"DC#{self.connection_id} dc connection success")
            self.emit("willCloseOnRemote")

        def on_close():
            logger.log(f"DC#{self.connection_id} dc closed for: {self.peer}")
            self.close()

        self.data_channel.on_open = on_open
        self.data_channel.on_close = on_close

    def add_stream(self, remote_stream: object) -> None:
        logger.log("Receiving stream", remote_stream)
        self._remote_stream = remote_stream
        super().emit("stream", remote_stream)

    def handle_message(self, message: dict) -> None:
        message_type = message['type']
        payload = message['payload']

        if message_type == ServerMessageType.Answer:
            self._negotiator.handle_sdp(message_type, payload['sdp'])
            self._open = True
        elif message_type == ServerMessageType.Candidate:
            self._negotiator.handle_candidate(payload['candidate'])
        else:
            logger.warn(f"Unrecognized message type:{message_type} from peer:{self.peer}")

    def answer(self, stream: Optional[object] = None, options: dict = {}) -> None:
        if self._local_stream:
            logger.warn("Local stream already exists on this MediaConnection. Are you answering a call twice?")
            return

        self._local_stream = stream

        if options.get('sdpTransform'):
            self.options['sdpTransform'] = options['sdpTransform']

        self._negotiator.start_connection({
            **self.options.get('_payload', {}),
            '_stream': stream
        })

        messages = self.provider._get_messages(self.connection_id)
        for message in messages:
            self.handle_message(message)

        self._open = True

    def close(self) -> None:
        if self._negotiator:
            self._negotiator.cleanup()
            self._negotiator = None

        self._local_stream = None
        self._remote_stream = None

        if self.provider:
            self.provider._remove_connection(self)
            self.provider = None

        if self.options and self.options.get('_stream'):
            self.options['_stream'] = None

        if not self.open:
            return

        self._open = False
        super().emit("close")