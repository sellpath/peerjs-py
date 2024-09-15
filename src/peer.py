import random
import logging
from enum import Enum
from typing import Dict, List, Optional, Callable, Any, TypedDict, Union, Type

from src.util import Util
from src.socket import Socket
from src.mediaconnection import MediaConnection
from src.dataconnection.DataConnection import DataConnection
from src.api import API
from src.peer_error import PeerError
from src.enums import ServerMessageType, ConnectionType,PeerErrorType

class LogLevel(Enum):
    DISABLED = 0
    ERRORS = 1
    WARNINGS = 2
    ALL = 3

class ReferrerPolicy(Enum):
    # Add referrer policy options here
    NO_REFERRER = "no-referrer"
    ORIGIN = "origin"
    STRICT_ORIGIN = "strict-origin"
    # ... add other referrer policy options as needed

class SerializerMapping(TypedDict):
    __annotations__ = {
        str: Callable[[str, 'Peer', Any], DataConnection]
    }

class PeerOptions(TypedDict, total=False):
    debug: Optional[LogLevel]
    host: Optional[str]
    port: Optional[int]
    path: Optional[str]
    key: Optional[str]
    token: Optional[str]
    config: Optional[Dict[str, Any]]
    secure: Optional[bool]
    pingInterval: Optional[int]
    referrerPolicy: Optional[ReferrerPolicy]
    logFunction: Optional[Callable[[LogLevel, Any], None]]
    # serializers: Optional[Dict[str, Callable[[str, 'Peer', Any], DataConnection]]]
    # serializers: Optional[Dict[str, Type[DataConnection]]]
    serializers: Optional[SerializerMapping]

class PeerEvents(TypedDict):
    open: Callable[[str], None]
    connection: Callable[[DataConnection], None]
    call: Callable[['MediaConnection'], None]
    close: Callable[[], None]
    disconnected: Callable[[str], None]
    error: Callable[['PeerError'], None]

class ServerMessageType(Enum):
    OPEN = "OPEN"
    ERROR = "ERROR"
    ID_TAKEN = "ID_TAKEN"
    INVALID_KEY = "INVALID_KEY"
    LEAVE = "LEAVE"
    EXPIRE = "EXPIRE"
    OFFER = "OFFER"

class ConnectionType(Enum):
    DATA = "data"
    MEDIA = "media"

class Peer:
    DEFAULT_KEY = "peerjs"

    def __init__(self, id=None, options=None):
        self._options = options or {}
        self._api = API(self._options)
        self._socket = self._create_server_connection()

        self._id = None
        self._last_server_id = None

        self._destroyed = False
        self._disconnected = False
        self._open = False
        self._connections: Dict[str, List[Any]] = {}
        self._lost_messages: Dict[str, List[Any]] = {}

        if id:
            self._initialize(id)
        else:
            self._api.retrieve_id().then(self._initialize).catch(
                lambda error: self._abort(PeerErrorType.SERVER_ERROR, error)
            )

    def _create_server_connection(self):
        socket = Socket(
            self._options.get('secure', True),
            self._options.get('host', 'localhost'),
            self._options.get('port', 9000),
            self._options.get('path', '/'),
            self._options.get('key', self.DEFAULT_KEY),
            self._options.get('ping_interval', 5000)
        )

        socket.on('message', self._handle_message)
        socket.on('error', lambda error: self._abort(PeerErrorType.SOCKET_ERROR, error))
        socket.on('disconnected', self._on_disconnected)
        socket.on('close', self._on_close)

        return socket

    def _initialize(self, id: str):
        self._id = id
        self._socket.start(id, self._options.get('token'))

    def _handle_message(self, message):
        type_ = message['type']
        payload = message.get('payload', {})
        peer_id = message.get('src')

        if type_ == ServerMessageType.OPEN:
            self._last_server_id = self._id
            self._open = True
            self.emit('open', self._id)
        elif type_ == ServerMessageType.ERROR:
            self._abort(PeerErrorType.SERVER_ERROR, payload['msg'])
        # ... handle other message types ...

    def connect(self, peer: str, options=None):
        if self._disconnected:
            logging.warning("Cannot connect to new Peer after disconnecting from server.")
            self.emit_error(PeerErrorType.DISCONNECTED, "Cannot connect to new Peer after disconnecting from server.")
            return None

        data_connection = DataConnection(peer, self, options or {})
        self._add_connection(peer, data_connection)
        return data_connection

    def call(self, peer: str, stream, options=None):
        if self._disconnected:
            logging.warning("Cannot connect to new Peer after disconnecting from server.")
            self.emit_error(PeerErrorType.DISCONNECTED, "Cannot connect to new Peer after disconnecting from server.")
            return None

        if not stream:
            logging.error("To call a peer, you must provide a stream from your browser's `getUserMedia`.")
            return None

        media_connection = MediaConnection(peer, self, {**(options or {}), '_stream': stream})
        self._add_connection(peer, media_connection)
        return media_connection

    def _add_connection(self, peer_id: str, connection):
        if peer_id not in self._connections:
            self._connections[peer_id] = []
        self._connections[peer_id].append(connection)

    def destroy(self):
        if self._destroyed:
            return

        logging.info(f"Destroy peer with ID:{self._id}")
        self.disconnect()
        self._cleanup()
        self._destroyed = True
        self.emit('close')

    def disconnect(self):
        if self._disconnected:
            return

        current_id = self._id
        logging.info(f"Disconnect peer with ID:{current_id}")
        self._disconnected = True
        self._open = False
        self._socket.close()
        self._last_server_id = current_id
        self._id = None
        self.emit('disconnected', current_id)

    def reconnect(self):
        if self._disconnected and not self._destroyed:
            logging.info(f"Attempting reconnection to server with ID {self._last_server_id}")
            self._disconnected = False
            self._initialize(self._last_server_id)
        elif self._destroyed:
            raise Exception("This peer cannot reconnect to the server. It has already been destroyed.")
        elif not self._disconnected and not self._open:
            logging.error("In a hurry? We're still trying to make the initial connection!")
        else:
            raise Exception(f"Peer {self._id} cannot reconnect because it is not disconnected from the server!")

    def list_all_peers(self, callback: Callable[[List[str]], None] = None):
        def cb(peers):
            if callback:
                callback(peers)

        self._api.list_all_peers().then(cb).catch(
            lambda error: self._abort(PeerErrorType.SERVER_ERROR, error)
        )

    # ... other methods and helper functions ...