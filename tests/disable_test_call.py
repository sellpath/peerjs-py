import asyncio
import logging

import unittest
from unittest.mock import Mock, AsyncMock, patch, ANY
from peerjs_py.peer import Peer, PeerOptions, LogLevel, ReferrerPolicy, PeerErrorType
from peerjs_py.api import API
from peerjs_py.option_interfaces import PeerJSOption
from peerjs_py.logger import logger, LogLevel
from peerjs_py.enums import SocketEventType, PeerEventType
from aiortc import MediaStreamTrack
from aiortc import RTCPeerConnection, RTCSessionDescription, RTCIceCandidate, MediaStreamTrack, RTCDataChannel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MockRTCPeerConnection:
    def __init__(self):
        self.ice_connection_state = 'new'
        self.connection_state = 'new'
        self.local_description = None
        self.remote_description = None

    async def create_offer(self):
        return {'type': 'offer', 'sdp': 'mock_offer_sdp'}

    async def create_answer(self):
        return {'type': 'answer', 'sdp': 'mock_answer_sdp'}

    async def set_local_description(self, description):
        self.local_description = description

    async def set_remote_description(self, description):
        self.remote_description = description

    async def add_ice_candidate(self, candidate):
        pass

    def _simulate_ice_connection(self):
        self.ice_connection_state = 'checking'
        self.ice_connection_state = 'connected'
        self.connection_state = 'connected'

class MockMediaConnection:
    def __init__(self, peer, peer_id, stream):
        self.peer = peer
        self.peer_id = peer_id
        self.stream = stream
        self.peer_connection = MockRTCPeerConnection()
        self.on_stream_handlers = []

    async def answer(self, stream):
        answer = await self.peer_connection.create_answer()
        await self.peer_connection.set_local_description(answer)
        self.peer_connection._simulate_ice_connection()
        for handler in self.on_stream_handlers:
            handler(stream)

    def on(self, event, handler):
        if event == 'stream':
            self.on_stream_handlers.append(handler)



class TestVoiceConnection(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        logger.info("Setting up test...")
        self.peer1 = Peer("peer1")
        self.peer2 = Peer("peer2")
        self.connection_established = asyncio.Event()

        # Mock the necessary methods and properties
        self.peer1.call = AsyncMock()
        self.peer2.on = Mock()
        self.peer1.connect = AsyncMock()
        self.peer2.connect = AsyncMock()

        logger.info("Test setup complete")

    async def asyncTearDown(self):
        logger.info("Tearing down test...")
        await self.peer1.destroy()
        await self.peer2.destroy()
        logger.info("Test teardown complete")

    async def get_local_audio_stream(self):
        class MockAudioTrack:
            kind = "audio"
        class MockStream:
            def getTracks(self):
                return [MockAudioTrack()]
        return MockStream()

    async def test_voice_connection(self):
        logger.info("Starting voice connection test")

        local_stream = await self.get_local_audio_stream()

        # Set up the mock for peer2.on("call")
        mock_media_connection = MockMediaConnection(self.peer2, "peer1", local_stream)
        self.peer2.on.side_effect = lambda event, callback: callback(mock_media_connection) if event == "call" else None

        # Set up the mock for peer1.call
        self.peer1.call.return_value = mock_media_connection

        logger.info("Connecting peers...")
        await self.peer1.connect("peer2")
        await self.peer2.connect("peer1")

        logger.info("Peer1 initiating call...")
        call = await asyncio.wait_for(self.peer1.call("peer2", local_stream), timeout=5.0)
        logger.info("Peer1 call initiated")

        def on_stream(remote_stream):
            logger.info("Peer1 received remote stream")
            self.connection_established.set()

        call.on("stream", on_stream)


        try:
            logger.info("Waiting for voice connection to be established...")
            await asyncio.wait_for(self.connection_established.wait(), timeout=10.0)
            self.assertTrue(self.connection_established.is_set(), "Voice connection was not established")
            logger.info("Voice connection test passed")
        except asyncio.TimeoutError:
            logger.error("Timeout waiting for voice connection")
            logger.error(f"Peer1 state: {self.peer1.connection.state if hasattr(self.peer1, 'connection') else 'Unknown'}")
            logger.error(f"Peer2 state: {self.peer2.connection.state if hasattr(self.peer2, 'connection') else 'Unknown'}")
            self.fail("Timeout waiting for voice connection")

        # Add a short delay to allow for potential late events
        await asyncio.sleep(1)

if __name__ == "__main__":
    import unittest
    unittest.main()