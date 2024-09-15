from enum import Enum, auto

class ConnectionType(Enum):
    Data = "data"
    Media = "media"

class PeerErrorType(Enum):
    BrowserIncompatible = "browser-incompatible"
    Disconnected = "disconnected"
    InvalidID = "invalid-id"
    InvalidKey = "invalid-key"
    Network = "network"
    PeerUnavailable = "peer-unavailable"
    SslUnavailable = "ssl-unavailable"
    ServerError = "server-error"
    SocketError = "socket-error"
    SocketClosed = "socket-closed"
    UnavailableID = "unavailable-id"
    WebRTC = "webrtc"

class BaseConnectionErrorType(Enum):
    NegotiationFailed = "negotiation-failed"
    ConnectionClosed = "connection-closed"

class DataConnectionErrorType(Enum):
    NotOpenYet = "not-open-yet"
    MessageToBig = "message-too-big"

class SerializationType(Enum):
    Binary = "binary"
    BinaryUTF8 = "binary-utf8"
    JSON = "json"
    None_ = "raw"

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
    Error = "ERROR"
    IdTaken = "ID-TAKEN"
    InvalidKey = "INVALID-KEY"
    Leave = "LEAVE"
    Expire = "EXPIRE"