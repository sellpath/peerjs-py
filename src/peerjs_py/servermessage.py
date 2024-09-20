from enum import Enum
from peerjs_py.enums import ServerMessageType

class ServerMessage:
    def __init__(self, type: ServerMessageType, payload: any, src: str):
        self.type = type
        self.payload = payload
        self.src = src