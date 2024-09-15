from src.peer import Peer, SerializerMapping
from src.dataconnection.StreamConnection import MsgPack

class MsgPackPeer(Peer):
    _serializers: SerializerMapping = {
        "MsgPack": MsgPack,
        "default": MsgPack
    }