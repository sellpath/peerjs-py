from enum import Enum

class ServerMessageType(Enum):
    pass  # Assuming ServerMessageType is an enum, define its values here

class ServerMessage:
    def __init__(self, type: ServerMessageType, payload: any, src: str):
        self.type = type
        self.payload = payload
        self.src = src