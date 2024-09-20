import asyncio
import logging

from unittest import IsolatedAsyncioTestCase
from peerjs_py import Peer, MediaConnection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestVoiceConnection(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        logger.info("Setting up test...")
        self.peer1 = Peer("peer1")
        self.peer2 = Peer("peer2")
        self.connection_established = asyncio.Event()
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

        @self.peer2.on("call")
        async def on_call(media_connection):
            print("Peer2 received call")
            local_stream = await self.get_local_audio_stream()
            await media_connection.answer(local_stream)
            logger.info("Peer2 answered call")
            
            @media_connection.on("stream")
            def on_stream(remote_stream):
                print("Peer2 received remote stream")
                self.connection_established.set()

        logger.info("Connecting peers...")
        await self.peer1.connect("peer2")
        await self.peer2.connect("peer1")

        local_stream = await self.get_local_audio_stream()
        logger.info("Peer1 initiating call...")
        call = await asyncio.wait_for(self.peer1.call("peer2", local_stream), timeout=5.0)
        logger.info("Peer1 call initiated")

        @call.on("stream")
        def on_stream(remote_stream):
            logger.info("Peer1 received remote stream")

        try:
            logger.info("Waiting for voice connection to be established...")
            await asyncio.wait_for(self.connection_established.wait(), timeout=5.0)
            self.assertTrue(self.connection_established.is_set(), "Voice connection was not established")
            logger.info("Voice connection test passed")
        except asyncio.TimeoutError:
            logger.error("Timeout waiting for voice connection")
            self.fail("Timeout waiting for voice connection")


if __name__ == "__main__":
    import unittest
    unittest.main()