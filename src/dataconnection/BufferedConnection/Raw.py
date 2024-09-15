from enum import Enum
from src.dataconnection.BufferedConnection.BufferedConnection import BufferedConnection

class SerializationType(Enum):
    None_ = 0

class Raw(BufferedConnection):
    serialization = SerializationType.None_

    def _handle_data_message(self, data):
        super().emit("data", data)

    def _send(self, data, _chunked):
        self._buffered_send(data)