import random
import string
import io
from typing import Callable, Dict, List, Optional, Union
from peerjs_py.binarypack.binarypack import pack, unpack
from peerjs_py.supports import Supports
from peerjs_py.utils.validateId import validateId
from peerjs_py.utils.random_token import random_token
import aiortc
import asyncio
from peerjs_py.dataconnection.BufferedConnection.binaryPackChunker import BinaryPackChunker

class UtilSupportsObj:
    browser: bool
    webRTC: bool
    audioVideo: bool
    data: bool
    binaryBlob: bool
    reliable: bool

DEFAULT_CONFIG = {
    "iceServers": [
        {"urls": "stun:stun.l.google.com:19302"},
        # {
        #     "urls": [
        #         "turn:eu-0.turn.peerjs.com:3478",
        #         "turn:us-0.turn.peerjs.com:3478",
        #     ],
        #     "username": "peerjs",
        #     "credential": "peerjsp",
        # },
    ],
    "sdpSemantics": "unified-plan",
}

CHUNKED_MTU = 16300

class Util(BinaryPackChunker):
    def __init__(self):
        super().__init__()
        self.CLOUD_HOST = "0.peerjs.com"
        self.CLOUD_PORT = 443
        self.chunkedBrowsers = {"Chrome": 1, "chrome": 1}
        self.defaultConfig = DEFAULT_CONFIG
        self.supports_instance = Supports()
        self.browser = self.supports_instance.get_browser()
        self.browserVersion = self.supports_instance.get_version()
        self.pack = pack
        self.unpack = unpack
        self.supports = self._init_supports()
        self.validateId = validateId
        self.randomToken = random_token

    def noop(self) -> None:
        pass

    def _init_supports(self) -> UtilSupportsObj:
        supported = UtilSupportsObj()
        supported.browser = self.supports_instance.is_platform_supported()
        supported.webRTC = self.supports_instance.is_webrtc_supported()
        supported.audioVideo = False
        supported.data = False
        supported.binaryBlob = False
        supported.reliable = False

        if not supported.webRTC:
            return supported

        # Using aiortc for WebRTC support
        try:
            pc = aiortc.RTCPeerConnection()
            dc = pc.createDataChannel(
                label='test',
                ordered=True,
                protocol="",
                negotiated=False,
                id=None)

            supported.audioVideo = True
            supported.data = True
            supported.binaryBlob = True
            supported.reliable = dc.ordered

            # Clean up
            dc.close()  # RTCDataChannel.close
            # await pc.close()
        except Exception:
            pass

        return supported

    def blobToArrayBuffer(self, blob: bytes, cb: Callable[[Optional[bytes]], None]) -> io.BytesIO:
        buffer = io.BytesIO(blob)
        
        def on_load():
            cb(buffer.getvalue())
        
        # Simulate the FileReader behavior
        buffer.seek(0)
        on_load()
        
        return buffer

    def binaryStringToArrayBuffer(self, binary: str) -> bytes:
            byte_array = bytearray(len(binary))
            
            for i in range(len(binary)):
                byte_array[i] = ord(binary[i]) & 0xff
            
            return bytes(byte_array)
    
    def isSecure(self) -> bool:
        # This would depend on the specific environment where the code is running
        # e.g. return location.protocol === "https:";
        return True

util = Util()