import random
import asyncio
# import threading
import json
from enum import Enum
from typing import Dict, List, Optional, Callable, Any, TypedDict, Union, Type
from pyee.asyncio import AsyncIOEventEmitter

from peerjs_py.utils.validateId import validateId
from peerjs_py.socket import Socket
from peerjs_py.mediaconnection import MediaConnection
from peerjs_py.dataconnection.DataConnection import DataConnection
from peerjs_py.api import API
from peerjs_py.peer_error import PeerError
from peerjs_py.enums import ServerMessageType, ConnectionType, PeerErrorType, PeerEventType, SocketEventType, ConnectionEventType
from peerjs_py.logger import LogLevel, logger
from peerjs_py.dataconnection.BufferedConnection import Raw as RawSerializer, Json as JsonSerializer, BinaryPack as BinaryPackSerializer
from peerjs_py.utils.random_token import random_token

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



class Peer(AsyncIOEventEmitter):
    DEFAULT_KEY = "peerjs"

    def __init__(self, id=None, options=None):
        super().__init__() 
        self._options = options or {}
        self._api = API(self._options)
        self._socket = self._create_server_connection()

        self._id = id
        self._last_server_id = None

        self._destroyed = False
        self._disconnected = False
        self._open = False
        self._connections: Dict[str, List[Any]] = {}
        self._lost_messages: Dict[str, List[Any]] = {}
        
        # self._lock = threading.Lock()

        # Set path correctly.
        if self._options.get('path'):
            if self._options['path'][0] != "/":
                self._options['path'] = "/" + self._options['path']
            if self._options['path'][-1] != "/":
                self._options['path'] += "/"

        self._serializers: SerializerMapping = {
            'raw': RawSerializer.Raw,
            'json': JsonSerializer.Json,
            'binary': BinaryPackSerializer.BinaryPack,
            'binary-utf8': BinaryPackSerializer.BinaryPack,
            'default': BinaryPackSerializer.BinaryPack
        }

        # Update _serializers with user-provided options
        if self._options.get('serializers'):
            self._serializers.update(self._options['serializers'])
        # Ensure all serializers are callable
        for key, serializer in self._serializers.items():
            if not callable(serializer):
                raise TypeError(f"Serializer '{key}' must be callable")
        logger.debug(f"peer.__init__ id: {id} Done")

    def id(self):
        return self._id

    async def start(self):
        """Activate Peer instance."""
        logger.info(f"Starting peer with ID: {self._id}")
        try:
            self._socket = self._create_server_connection()
            await self._socket.start(id=self._id, token=self)
            logger.info("Successfully connected to signaling server")
        except Exception as e:
            logger.exception(f"Failed to connect to signaling server: {e}")
            await self.emit_error(PeerErrorType.SocketError.value, "Could not connect to signaling server")
            return
        # Sanity checks
        # Ensure alphanumeric id
        if self._id and not validateId(self._id):
            logger.error('Peer validateId failed: %s', self._id)
            self._delayedAbort(PeerErrorType.InvalidID,
                               f'ID "{self._id}" is invalid')
            return

        if self._id is None:
            try:
                logger.debug('Peer start()self._id: %s', self._id)
                id = await self._api.retrieve_id()
                self._id = id
                logger.debug('Peer retrieve_id: %s', self._id)
            except Exception as e:
                await self._abort(PeerErrorType.SERVER_ERROR, e)
                return
            
        await self._initialize(self._id)

        # await self._socket.start(self._id, self._options.get('token'))
        logger.info('Peer started with ID: %s', self._id)

    def _create_server_connection(self):
        logger.debug(f"_create_server_connection with options: {self._options}")
        socket = Socket(
            self._options.get('secure', True),
            self._options.get('host', 'localhost'),
            self._options.get('port', 9000),
            self._options.get('path', '/'),
            self._options.get('key', self.DEFAULT_KEY),
            self._options.get('ping_interval', 5)
        )

        # socket.on(SocketEventType.Message.value, self._handle_message)
        socket.on(SocketEventType.Message.value, lambda msg: asyncio.create_task(self._handle_message(msg)))
        socket.on(SocketEventType.Error.value, lambda error: self._abort(PeerErrorType.SocketError, error))
        socket.on(SocketEventType.Disconnected.value, self._on_disconnected)
        socket.on(SocketEventType.Close.value, self._on_close)

        logger.debug(f"_create_server_connection with options: {self._options} : Done")
        return socket

    async def _on_disconnected(self):
        if self._disconnected:
            return
        logger.warning("Lost connection to signaling server.")
        await self.emit_error(PeerErrorType.Network.value, "Lost connection to server.")
        await self.disconnect()

    def _on_close(self):
        logger.debug(f"peer socket close event id: {self._id}")
        if self._disconnected:
            self._abort(PeerErrorType.SocketClosed,
                                "Underlying socket is already closed.")


    async def _initialize(self, id: str):
        self._id = id
        await self._socket.start(id, self._options.get('token'))

    async def _handle_message(self, message):
        logger.debug(f"peer  on socket.on {SocketEventType.Message.value} message: {message}")
        type_ = message['type']
        payload = message.get('payload', {})
        peer_id = message.get('src')

        if type_ == ServerMessageType.Open.value:
            self._last_server_id = self._id
            self._open = True
            self.emit(PeerEventType.Open.value, self._id)
        elif type_ == ServerMessageType.Error.value:
            await self._abort(PeerErrorType.SERVER_ERROR, payload['msg'])
        elif type_ == ServerMessageType.IdTaken.value:
            await self._abort(PeerErrorType.UnavailableID, f'ID "{self._id}" is taken')
        elif type_ == ServerMessageType.InvalidKey.value:
            await self._abort(PeerErrorType.InvalidKey, f'API KEY "{self._options.get("key")}" is invalid')
        elif type_ == ServerMessageType.Leave.value:
            logger.log(f"Received leave message from {peer_id}")
            self._cleanup_peer(peer_id)
            self._connections.pop(peer_id, None)
        elif type_ == ServerMessageType.Expire.value:
            await self.emit_error(PeerErrorType.PeerUnavailable.value, f"Could not connect to peer {peer_id}")
        elif type_ == ServerMessageType.Offer.value:
            connection_id = payload['connectionId']
            connection = self.get_connection(peer_id, connection_id)

            if connection:
                await connection.close()
                logger.warning(f"Offer received for existing Connection ID:{connection_id}")

            if payload['type'] == ConnectionType.Media.value:
                media_connection = MediaConnection(peer_id, self, {
                    'connection_id': connection_id,
                    '_payload': payload,
                    'metadata': payload.get('metadata')
                })
                await media_connection.initialize() # no effect as no _stream passed
                connection = media_connection
                self._add_connection(peer_id, connection)
                self.emit(PeerEventType.Call.value, media_connection)

            elif payload['type'] == ConnectionType.Data.value:
                serializer = self._serializers.get(payload['serialization'])
                if not serializer:
                    logger.warning(f"Unknown serialization type: {payload['serialization']}")
                    return
                
                DataConnectionClass =  self._serializers.get(payload['serialization'])
                if not DataConnectionClass:
                    logger.error(f"Unknown serialization type: {payload['serialization']}")
                    await self.emit_error(PeerErrorType.InvalidSerialization.value, f"Unknown serialization type: {payload['serialization']}")
                    return None
                
                data_connection = DataConnectionClass(
                    peer_id,
                    self,
                    {
                        'connectionId': connection_id,
                        '_payload': payload,
                        'metadata': payload.get('metadata'),
                        'label': payload.get('label'),
                        'serialization': payload['serialization'],
                        'reliable': payload.get('reliable')
                    }
                )

                data_connection.connection_id = connection_id

                data_connection._negotiator.on_data_channel_org=data_connection._negotiator.on_data_channel 
                data_channel_initialized = asyncio.Future()
                async def on_data_channel_wrapper(channel):
                    await data_connection._initialize_data_channel(channel)
                    await data_connection._negotiator.on_data_channel_org(channel)
                    data_channel_initialized.set_result(True)

                data_connection._negotiator.on_data_channel = on_data_channel_wrapper

                await data_connection._negotiator.start_connection({
                    'originator': False,
                    'sdp': payload.get('sdp'),
                    'connectionId': connection_id
                })
                logger.info(f"wait data_channel_initialized connection_id:{connection_id}")
                await data_channel_initialized
                # await data_connection.open_future
                logger.info(f"wait data_channel_initialized connection_id:{connection_id} done")
                if not data_connection._open: # assume it's response to connect, so should be opened. just workaround as it does not triggered by on_data_channel->data_channel.on("open") event.
                    data_connection._open = True
                    data_connection.open_future.set_result(True)

                connection = data_connection
                logger.info(f"serializer data_connection for {payload['serialization']}")
                self._add_connection(peer_id, connection)
                logger.info(f"Connection added, current connections: {self._connections}")
                self.emit(PeerEventType.Connection.value, data_connection)
            else:
                logger.warning(f"Received malformed connection type:{payload['type']}")
                return

            msgs_rcvd_before_data_conn = self._get_messages(connection_id)
            logger.debug(f"connection_id: {connection_id} handle previous message: {len(msgs_rcvd_before_data_conn)}  current message: {message}")
            if msgs_rcvd_before_data_conn:
                for msg_rcvd_before_data_conn in msgs_rcvd_before_data_conn:
                    await connection.handle_message(msg_rcvd_before_data_conn)

            # logger.debug(f"connection_id: {connection_id} handle current message ===> check if this is right")
            # await connection.handle_message(message)

        else:
            if not payload:
                logger.warning(f"_handle_message : malformed no payload message from peer_id:{peer_id} of type {type_}")
                return

            connection_id = payload.get('connectionId')
            connection = self.get_connection(peer_id, connection_id)

            if connection and connection.peer_connection:
                logger.debug(f"connection Pass message peer_id:{peer_id} of type:{type_} to connection_id:{connection_id}")
                #pass to next connection
                await connection.handle_message(message)
            # elif connection:  # to be fixed
            #     logger.debug(f"connection exists but peer_connection not ready, handling message directly")
            #     await connection.handle_message(message)
            elif connection_id:
                logger.debug(f"store message peer_id:{peer_id} of type:{type_} to connection_id: {connection_id} but connection.peer_connection not ready")
                self._store_message(connection_id, message)
            else:
                logger.warning("You received an unrecognized message:", message)


    async def connect(self, peer_id: str, options: Dict[str, Any] = None):
        if self._disconnected:
            logger.warning(
                "You cannot connect to a new Peer because you called .disconnect() on this Peer and ended your connection with the server. You can create a new Peer to reconnect, or call reconnect() on this peer if you believe its ID to still be available."
            )
            await self.emit_error(PeerErrorType.Disconnected.value, "Cannot connect to new Peer after disconnecting from server.")
            return None

        options = options or {}
        connection_id = f"dc_{random_token()}"
        options["_payload"] = {
            "originator": True,
            "reliable": options.get("reliable", True),
            "connectionId": connection_id
        }
        serialization = options.get('serialization', 'json')
        # Get the appropriate DataConnection subclass
        DataConnectionClass = self._serializers.get(serialization)
        if not DataConnectionClass:
            logger.error(f"Unknown serialization type: {serialization}")
            await self.emit_error(PeerErrorType.InvalidSerialization.value, f"Unknown serialization type: {serialization}")
            return None

        try:
            logger.debug(f"connect peer_id:{peer_id} options: {options}")
            data_connection = DataConnectionClass(peer_id, self, options)
            data_connection.connection_id = connection_id
            logger.debug(f"connect peer_id:{peer_id} options: {options} data_connection.initialize()")
            await data_connection.initialize()
            self._add_connection(peer_id, data_connection)
            logger.info(f"Connection initialized for peer_id:{peer_id} _add_connection added")

            logger.debug(f"Waiting for data channel to open for peer_id:{peer_id}")
            await asyncio.wait_for(data_connection.open_future, timeout=1)
            logger.info(f"Data channel opened for peer_id:{peer_id}")
        except asyncio.TimeoutError:
            logger.warning(f"Timeout waiting for data channel to open for peer_id:{peer_id}, but continuing anyway")
        except Exception as e:
            logger.exception(f"Error {e} while DataConnection and initialize")
            # raise e
        return data_connection
    
    def _add_connection(self, peer_id: str, connection):
        if peer_id not in self._connections:
            self._connections[peer_id] = []
        logger.info(f"_add_connection : peer_id: {peer_id}  connection: {connection.connection_id}")
        self._connections[peer_id].append(connection)
        # Add this line to log the current state of connections
        logger.info(f"Current connections after adding: {self._connections}")

    def get_connection(self, peer_id: str, connection_id: str) -> Optional[Union[DataConnection, MediaConnection]]:
        """
        Retrieve a connection by peer ID and connection ID.
        
        :param peer_id: The ID of the peer.
        :param connection_id: The ID of the connection.
        :return: The connection if found, otherwise None.
        """
        logger.info(f"Searching for connection - peer_id: {peer_id}, connection_id: {connection_id}")
        logger.info(f"Current connections: {self._connections}")
        if not peer_id:
            logger.error(f"get_connection ==> peer_id none")
            return None
        connections = self._connections.get(peer_id, [])
        for connection in connections:
            if connection.connection_id == connection_id:
                logger.info(f"get_connection : Found peer_id: {peer_id}  connection: {connection_id} connection: {connection}")
                return connection
        logger.warning(f"get_connection : Failed peer_id: {peer_id}  connection: {connection_id} connections:{connections}  self._connections: {self._connections}")
        return None
    
    async def call(self, peer_id: str, stream: Any, options: Dict[str, Any] = None) -> MediaConnection:
        logger.info(f"Initiating call from {self._id} to {peer_id}")
        if not options:
            options = {
                "_stream": stream,
            }
        if self._disconnected:
            logger.warning("Cannot connect to new Peer after disconnecting from server.")
            self.emit_error(PeerErrorType.Disconnected.value, "Cannot connect to new Peer after disconnecting from server.")
            return None

        if not stream:
            logger.error("To call a peer, you must provide a stream from your browser's `getUserMedia`.")
            return None
        
        media_connection = MediaConnection(peer_id, self, {**(options or {}), '_stream': stream})
        logger.info(f"MediaConnection created for call from {self._id} to {peer_id}")

        @media_connection.on('stream')
        def on_stream(remote_stream):
            logger.info(f"Received remote stream on_stream for connection: {media_connection.connection_id}")

        await media_connection.initialize()
        logger.info(f"MediaConnection initialized for call from {self._id} to {peer_id}")
        
        self._add_connection(peer_id, media_connection)
        return media_connection

    async def _remove_connection(self, connection):
        """Remove a connection from the list of connections."""
        if connection.peer in self._connections:
            self._connections[connection.peer].remove(connection)
            if not self._connections[connection.peer]:
                del self._connections[connection.peer]
        
        if connection.peer in self._lost_messages:
            del self._lost_messages[connection.peer]


    async def _cleanup(self) -> None:
        """Disconnects every connection on this peer."""
        # we need to iterate over a copy
        # in order to remove elements from the original dict
        keys_copy = list(self._connections.keys())
        for peerId in keys_copy:
            await self._cleanupPeer(peerId)
            self._connections.pop(peerId, None)
        if self._socket:
            await self._socket._cleanup()
            # await self._socket.remove_all_listeners()
        #    await self._api.close()

    async def _cleanupPeer(self, peerId: str) -> None:
        """Close all connections to this peer."""
        connections = self._connections.get(peerId)
        if not connections:
            return
        for connection in connections:
            await connection.close()

    async def _abort(self, type: PeerErrorType, message: str) -> None:
        """Emit an error message and destroy the Peer.

        The Peer is not destroyed if it's in a disconnected state,
        in which case
        it retains its disconnected state and its existing connections.
        """
        logger.error('Aborting! \n'
                  'PeerErrorType: %s \n'
                  'Error message: %s',
                  type,
                  message)
        await self.emit_error(type, message)
        if not self._last_server_id:
            await self.destroy()
        else:
            await self.disconnect()

    async def emit_error(self, type: PeerErrorType, err: str) -> None:
        """Emit a typed error message."""
        logger.warning(f'Connection error: type:{type} %s', err)
        if isinstance(err, str):
            err = RuntimeError(err)
        else:
            assert isinstance(err, Exception)
        # logger.warning('Connection error: \n%s', err)
        err.type = type
        self.emit(PeerEventType.Error.value, err)

    async def destroy(self):
        logger.info(f"TRY destroy peer with ID:{ self._id}")
        if self._destroyed:
            return

        logger.info(f"Destroy peer with ID:{self._id}")
        await self.disconnect()
        await self._cleanup()
        self._destroyed = True
        self.emit(PeerEventType.Close.value)

    async def disconnect(self):
        if self._disconnected:
            logger.info(f"disconnect peer with ID already disconnected:{ self._id}")
            return

        current_id = self._id
        logger.info(f"Disconnect peer with ID:{current_id}")
        self._disconnected = True
        self._open = False
        if (self._socket is not None):
            await self._socket.close()
        logger.info(f"Disconnect _last_server_id ID:{current_id}")
        self._last_server_id = current_id
        self._id = None
        self.emit(PeerEventType.Disconnected.value, current_id)

    async def reconnect(self):
        if self._disconnected and not self._destroyed:
            logger.info(f"Attempting reconnection to server with ID {self._last_server_id}")
            self._disconnected = False
            await self._initialize(self._last_server_id)
            await self.start()
        elif self._destroyed:
            raise Exception("This peer cannot reconnect to the server. It has already been destroyed.")
        elif not self._disconnected and not self._open:
            logger.error("In a hurry? We're still trying to make the initial connection!")
        else:
            raise Exception(f"Peer {self._id} cannot reconnect because it is not disconnected from the server!")

    # async def list_all_peers(self, callback: Optional[Callable[[List[str]], None]] = None) -> List[str]:
    #     try:
    #         peers = await self._api.list_all_peers()
    #         if callback:
    #             callback(peers)
    #         return peers
    #     except Exception as error:
    #         self.emitError(PeerErrorType.SERVER_ERROR, str(error))
    #         return []
        
    async def list_all_peers(self) -> List[str]:
        if not self._api:
            raise Exception("API not initialized")
        try:
            return await self._api.list_all_peers()
        except Exception as error:
            await self.emit_error(PeerErrorType.SERVER_ERROR, str(error))
            return []
        

    def _store_message(self, connection_id: str, message: Any) -> None:
        """Stores messages without a set up connection, to be claimed later."""
        if connection_id not in self._lost_messages:
            self._lost_messages[connection_id] = []
        self._lost_messages[connection_id].append(message)

    def _get_messages(self, connection_id: str) -> List[Any]:
        """Retrieve messages from lost message store."""
        messages = self._lost_messages.get(connection_id, [])
        if messages:
            del self._lost_messages[connection_id]
        return messages
