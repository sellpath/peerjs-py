from peerjs_py.peer import Peer, SerializerMapping
from peerjs_py.dataconnection.StreamConnection import MsgPack

class MsgPackPeer(Peer):
    _serializers: SerializerMapping = {
        "MsgPack": MsgPack,
        "default": MsgPack
    }