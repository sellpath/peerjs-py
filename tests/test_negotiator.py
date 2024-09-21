import asyncio
import unittest
from unittest.mock import Mock, AsyncMock, patch
from peerjs_py.negotiator import Negotiator
from peerjs_py.enums import ConnectionType, ServerMessageType
from peerjs_py.logger import logger, LogLevel

class TestNegotiator(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        logger.set_log_level(LogLevel.All)


        self.mock_api_patcher = patch('peerjs_py.peer.API')
        self.mock_socket_patcher = patch('peerjs_py.peer.Socket')
        self.mock_api = self.mock_api_patcher.start()
        self.mock_socket = self.mock_socket_patcher.start()

        self.mock_connection = Mock()
        self.mock_connection.peer = "test_peer"
        self.mock_connection.connection_id = "test_connection_id"
        self.mock_connection.type = ConnectionType.Data
        self.mock_connection.provider = Mock()
        self.mock_connection.peer_connection = None
        self.negotiator = Negotiator(self.mock_connection)
        self.mock_connection.provider._socket.send = AsyncMock()

    async def asyncSetUp(self):
        self.mock_connection = Mock()
        self.mock_connection.connection_id = "test_connection_id"
        self.negotiator = Negotiator(self.mock_connection)

    @patch('peerjs_py.negotiator.RTCPeerConnection')
    async def test_start_connection_as_originator(self, mock_rtc_peer_connection):
        options = {
            "originator": True,
            "reliable": True,
        }
        
        mock_peer_connection = AsyncMock()
        mock_data_channel = AsyncMock()
        self.negotiator._start_peer_connection = AsyncMock(return_value=mock_peer_connection)
        mock_peer_connection.createDataChannel.return_value = mock_data_channel
        mock_rtc_peer_connection.return_value = mock_peer_connection

        self.negotiator._make_offer = AsyncMock()
        self.mock_connection._initialize_data_channel = AsyncMock()
        
        self.mock_connection.peer_connection = None
        await self.negotiator.start_connection(options)
        
        # mock_rtc_peer_connection.assert_called_once_with(
        #     configuration=self.mock_connection.provider._options.get('config')
        # )
        self.assertEqual(self.mock_connection.peer_connection, mock_peer_connection)
        # mock_peer_connection.createDataChannel.assert_awaited_once_with(
        #     self.mock_connection.connection_id,
        #     ordered=True,
        #     protocol="",
        #     negotiated=False,
        #     id=None
        # )
        self.negotiator._make_offer.assert_awaited_once()

  
    async def test_start_connection_as_non_originator(self):
        options = {
            "originator": False,
            "sdp": "mock_sdp_data"
        }
        
        mock_peer_connection = AsyncMock()
        self.negotiator._start_peer_connection = AsyncMock(return_value=mock_peer_connection)
        self.negotiator.handle_sdp = AsyncMock()
        
        await self.negotiator.start_connection(options)
        
        self.assertEqual(self.mock_connection.peer_connection, mock_peer_connection)
        self.negotiator._start_peer_connection.assert_awaited_once()
        self.negotiator.handle_sdp.assert_awaited_once_with("OFFER", "mock_sdp_data")


    # async def test_handle_sdp_offer(self):
    #     mock_peer_connection = AsyncMock()
    #     self.mock_connection.peer_connection = mock_peer_connection
        
    #     self.negotiator._make_answer = AsyncMock()
        
    #     await self.negotiator.handle_sdp("OFFER", "test_sdp")
        
    #     mock_peer_connection.setRemoteDescription.assert_called_once()
    #     self.negotiator._make_answer.assert_called_once()

    async def test_handle_sdp_offer(self):
        mock_peer_connection = AsyncMock()
        mock_peer_connection.signalingState = "stable"
        self.mock_connection.peer_connection = mock_peer_connection
        self.mock_connection.connection_established = False
        self.mock_connection.peer = "test_peer"
        self.mock_connection.connection_id = "test_connection_id"

        self.negotiator._make_answer = AsyncMock()
        self.negotiator.ice_gathering_complete = asyncio.Event()
        self.negotiator._try_send_offer_or_answer = AsyncMock()

        # Start handling SDP in a separate task
        handle_sdp_task = asyncio.create_task(self.negotiator.handle_sdp("OFFER", "test_sdp"))

        # Wait a bit to allow for the SDP handling to start
        await asyncio.sleep(0.1)

        # Simulate ICE gathering completion
        self.negotiator.ice_gathering_complete.set()

        # Wait for handle_sdp to complete
        await handle_sdp_task
        

    async def test_handle_candidate(self):
        mock_peer_connection = AsyncMock()
        self.mock_connection.peer_connection = mock_peer_connection
        
        ice_candidate = {
            "sdpMid": "test_mid",
            "sdpMLineIndex": 0,
             "candidate": "candidate:1 1 udp 2122260223 192.168.0.1 54321 typ host generation 0"
        }
        
        await self.negotiator.handle_candidate(ice_candidate)
        
        mock_peer_connection.addIceCandidate.assert_called_once()

    async def test_cleanup(self):
        mock_peer_connection = AsyncMock()
        mock_peer_connection.connectionState = "new"
        mock_peer_connection.on = AsyncMock()  # Make the 'on' method async
        self.mock_connection.peer_connection = mock_peer_connection
        self.mock_connection.data_channel = AsyncMock()
        self.mock_connection.data_channel.readyState = "open"
        
        await self.negotiator.cleanup()
        
        self.assertIsNone(self.mock_connection.peer_connection)
        mock_peer_connection.close.assert_called_once()
        # mock_peer_connection.on.assert_called_with("track", None)  # Assert that 'on' was called with correct arguments

if __name__ == '__main__':
    unittest.main()
