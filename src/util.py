import random
import string
from typing import Callable, Dict, List, Optional, Union
from src.binarypack.binarypack import pack, unpack
from src.supports import Supports
from src.utils.validateId import validateId
from src.utils.random_token import random_token
import aiortc
import asyncio

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
        {
            "urls": [
                "turn:eu-0.turn.peerjs.com:3478",
                "turn:us-0.turn.peerjs.com:3478",
            ],
            "username": "peerjs",
            "credential": "peerjsp",
        },
    ],
    "sdpSemantics": "unified-plan",
}

class Util:
    def __init__(self):
        self.CLOUD_HOST = "0.peerjs.com"
        self.CLOUD_PORT = 443
        self.chunkedBrowsers = {"Chrome": 1, "chrome": 1}
        self.defaultConfig = DEFAULT_CONFIG
        self.supports_instance = Supports()
        self.browser = self.supports_instance.get_browser()
        self.browserVersion = self.supports_instance.get_version()
        self.pack = pack
        self.unpack = unpack
        # self.supports = self._init_supports()
        self.supports = asyncio.run(self._init_supports())
        self.validateId = validateId
        self.randomToken = random_token

    def noop(self) -> None:
        pass

    async def _init_supports(self) -> UtilSupportsObj:
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
            dc = pc.createDataChannel('test')

            supported.audioVideo = True
            supported.data = True
            supported.binaryBlob = True
            supported.reliable = dc.ordered

            # Clean up
            dc.close()
            await pc.close()
        except Exception:
            pass

        return supported

    def blobToArrayBuffer(self, blob: bytes, cb: Callable[[Optional[bytes]], None]) -> None:
        cb(blob)

    def binaryStringToArrayBuffer(self, binary: str) -> bytes:
        return binary.encode('utf-8')

    def isSecure(self) -> bool:
        # This would depend on the specific environment where the code is running
        return True  # Placeholder

util = Util()