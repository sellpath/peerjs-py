from abc import ABC, abstractmethod
from typing import Any, Dict, Union, TypeVar, Generic
from enum import Enum
from aiortc import RTCPeerConnection, RTCDataChannel
from pyee.asyncio import AsyncIOEventEmitter
from peerjs_py.enums import ConnectionEventType, ConnectionType, BaseConnectionErrorType, ServerMessageType
from peerjs_py.peer_error import PeerError, EventEmitterWithError
from peerjs_py.servermessage import ServerMessage


class BaseConnection(EventEmitterWithError[Union[str, BaseConnectionErrorType]], ABC):
    def __init__(self, peer: str, provider, options: Dict[str, Any]):
        super().__init__()
        self._open = False
        self.metadata = options.get('metadata')
        self.connection_id: str = options.get('connection_id', '')
        self.peer_connection: RTCPeerConnection = RTCPeerConnection()
        self.data_channel: RTCDataChannel = None
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