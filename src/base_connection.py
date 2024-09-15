from abc import ABC, abstractmethod
from typing import Any, Dict, Union, TypeVar, Generic
from enum import Enum
from aiortc import RTCPeerConnection, RTCDataChannel
from pyee.asyncio import AsyncIOEventEmitter

class ConnectionType(Enum):
    DATA = "data"
    MEDIA = "media"

class BaseConnectionErrorType(Enum):
    PEER_UNAVAILABLE = "peer-unavailable"
    CONNECTION_ERROR = "connection-error"
    DISCONNECTED = "disconnected"

class PeerError(Exception):
    pass

T = TypeVar('T', bound=Union[str, BaseConnectionErrorType])

class EventEmitterWithError(AsyncIOEventEmitter, Generic[T]):
    def emit_error(self, error: T, *args: Any) -> bool:
        return self.emit('error', error, *args)

class Peer:
    # Placeholder for Peer class implementation
    pass

class ServerMessage:
    # Placeholder for ServerMessage class implementation
    pass

class BaseConnection(EventEmitterWithError[Union[str, BaseConnectionErrorType]], ABC):
    def __init__(self, peer: str, provider: Peer, options: Dict[str, Any]):
        super().__init__()
        self._open = False
        self.metadata = options.get('metadata')
        self.connectionId: str = options.get('connectionId', '')
        self.peerConnection: RTCPeerConnection = RTCPeerConnection()
        self.dataChannel: RTCDataChannel = None
        self.peer = peer
        self.provider = provider
        self.options = options
        self.label: str = options.get('label', '')

    @property
    @abstractmethod
    def type(self) -> ConnectionType:
        pass

    @property
    def open(self) -> bool:
        return self._open

    @abstractmethod
    async def close(self) -> None:
        pass

    @abstractmethod
    async def handle_message(self, message: ServerMessage) -> None:
        pass

    @abstractmethod
    async def _initialize_data_channel(self, dc: RTCDataChannel) -> None:
        pass

    class Events:
        # Define any common events here
        pass
    # Add other necessary methods and properties here