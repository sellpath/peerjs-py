from abc import ABC, abstractmethod
from typing import Any, Dict, Union
from enum import Enum

class ConnectionType(Enum):
    pass

class BaseConnectionErrorType(Enum):
    pass

class PeerError(Exception):
    pass

class EventEmitterWithError:
    pass

class Peer:
    pass

class ServerMessage:
    pass

class BaseConnection(EventEmitterWithError, ABC):
    def __init__(self, peer: str, provider: Peer, options: Dict[str, Any]):
        super().__init__()
        self._open = False
        self.metadata = options.get('metadata')
        self.connectionId: str
        self.peerConnection: Any  # RTCPeerConnection equivalent
        self.dataChannel: Any  # RTCDataChannel equivalent
        self.peer = peer
        self.provider = provider
        self.options = options
        self.label: str

    @property
    @abstractmethod
    def type(self) -> ConnectionType:
        pass

    @property
    def open(self) -> bool:
        return self._open

    @abstractmethod
    def close(self) -> None:
        pass

    @abstractmethod
    def handle_message(self, message: ServerMessage) -> None:
        pass

    @abstractmethod
    def _initialize_data_channel(self, dc: Any) -> None:  # RTCDataChannel equivalent
        pass