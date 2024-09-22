import json
from enum import Enum, unique, auto

@unique
class ConnectionEventType(Enum):
    """Connection event types."""
    Open = "open"
    Stream = "stream"
    Data = "data"
    Close = "close"
    Error = "error"
    IceStateChanged = "iceStateChanged"


class ConnectionType(Enum):
    Data = "data"
    Media = "media"

@unique
class PeerEventType(Enum):
    """Peer event type."""
    Open = "open"
    Close = "close"
    Connection = "connection"
    Call = "call"
    Disconnected = "disconnected"
    Error = "error"

@unique
class PeerErrorType(Enum):
    BrowserIncompatible = "browser-incompatible"
    Disconnected = "disconnected"
    InvalidID = "invalid-id"
    InvalidKey = "invalid-key"
    Network = "network"
    PeerUnavailable = "peer-unavailable"
    SslUnavailable = "ssl-unavailable"
    SERVER_ERROR = "server-error"
    SocketError = "socket-error"
    SocketClosed = "socket-closed"
    UnavailableID = "unavailable-id"
    WebRTC = "webrtc"
    InvalidSerialization= "invalid-serialization"

class BaseConnectionErrorType(Enum):
    PEER_UNAVAILABLE = "peer-unavailable"
    CONNECTION_ERROR = "connection-error"
    DISCONNECTED = "disconnected"
    NegotiationFailed = "negotiation-failed"
    ConnectionClosed = "connection-closed"

class DataConnectionErrorType(Enum):
    NotOpenYet = "not-open-yet"
    MessageToBig = "message-too-big"

class SerializationType(Enum):
    Binary = "binary"
    BinaryUTF8 = "binary-utf8"
    JSON = "json"
    # Raw is passed without any modifications
    Raw = 'raw'


class SocketEventType(Enum):
    Message = "message"
    Disconnected = "disconnected"
    Error = "error"
    Close = "close"

class ServerMessageType(Enum):
    Heartbeat = "HEARTBEAT"
    Candidate = "CANDIDATE"
    Offer = "OFFER"
    Answer = "ANSWER"
    Open = "OPEN"
    Error = "ERROR"  # Server error.
    IdTaken = "ID-TAKEN"  #The selected ID is taken.
    InvalidKey = "INVALID-KEY" # The given API key cannot be found.
    Leave = "LEAVE" # Another peer has closed its connection to this peer.
    Expire = "EXPIRE" # The offer sent to a peer has expired without response.



class EnumAwareJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Enum):
            return obj.value
        return super().default(obj)