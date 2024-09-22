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

        test_sdp = {'sdp': 'v=0\r\no=- 3935971857 3935971857 IN IP4 0.0.0.0\r\ns=-\r\nt=0 0\r\na=group:BUNDLE 0 1\r\na=msid-semantic:WMS *\r\nm=audio 53774 UDP/TLS/RTP/SAVPF 96 0 8\r\nc=IN IP6 2601:646:8f02:600:d8:d3e4:1b06:dfb2\r\na=sendrecv\r\na=extmap:1 urn:ietf:params:rtp-hdrext:sdes:mid\r\na=extmap:2 urn:ietf:params:rtp-hdrext:ssrc-audio-level\r\na=mid:0\r\na=msid:ec8cd828-4c36-4b98-9c48-af09e526a238 3ca954ea-8a5c-4b7d-b91c-5a1925aea3d2\r\na=rtcp:9 IN IP4 0.0.0.0\r\na=rtcp-mux\r\na=ssrc:2462290723 cname:acb22674-4ee5-40c6-a254-ae9af40f8214\r\na=rtpmap:96 opus/48000/2\r\na=rtpmap:0 PCMU/8000\r\na=rtpmap:8 PCMA/8000\r\na=candidate:1123667dfdc374ae854ce9b6bf98cdb0 1 udp 2130706431 2601:646:8f02:600:d8:d3e4:1b06:dfb2 53774 typ host\r\na=candidate:b1d94ce8d45d08769c52cd83bb5bef98 1 udp 2130706431 2601:646:8f02:600:e09c:96b7:c193:7fce 49832 typ host\r\na=candidate:4f322c660417b6096fd16770d34b336f 1 udp 2130706431 192.168.0.20 61867 typ host\r\na=candidate:d91acf2eb43ce6326327b73ea4751498 1 udp 1694498815 76.133.22.95 61867 typ srflx raddr 192.168.0.20 rport 61867\r\na=end-of-candidates\r\na=ice-ufrag:Vxsn\r\na=ice-pwd:85LMqfOCusaVGHQlJvVAUU\r\na=fingerprint:sha-256 77:93:09:A1:6D:16:67:EE:7B:19:04:0A:1A:78:7B:EE:40:58:10:A7:5E:B8:F1:92:D6:46:A6:76:AE:0D:CE:1C\r\na=setup:actpass\r\nm=application 54437 DTLS/SCTP 5000\r\nc=IN IP6 2601:646:8f02:600:d8:d3e4:1b06:dfb2\r\na=mid:1\r\na=sctpmap:5000 webrtc-datachannel 65535\r\na=max-message-size:65536\r\na=candidate:1123667dfdc374ae854ce9b6bf98cdb0 1 udp 2130706431 2601:646:8f02:600:d8:d3e4:1b06:dfb2 54437 typ host\r\na=candidate:b1d94ce8d45d08769c52cd83bb5bef98 1 udp 2130706431 2601:646:8f02:600:e09c:96b7:c193:7fce 63394 typ host\r\na=candidate:4f322c660417b6096fd16770d34b336f 1 udp 2130706431 192.168.0.20 63362 typ host\r\na=candidate:d91acf2eb43ce6326327b73ea4751498 1 udp 1694498815 76.133.22.95 63362 typ srflx raddr 192.168.0.20 rport 63362\r\na=end-of-candidates\r\na=ice-ufrag:pg1C\r\na=ice-pwd:8opIVLySv63Mj3nZIeY4eh\r\na=fingerprint:sha-256 77:93:09:A1:6D:16:67:EE:7B:19:04:0A:1A:78:7B:EE:40:58:10:A7:5E:B8:F1:92:D6:46:A6:76:AE:0D:CE:1C\r\na=setup:actpass\r\n', 'type': 'offer'}
                    
        # Start handling SDP in a separate task
        handle_sdp_task = asyncio.create_task(self.negotiator.handle_sdp("OFFER", test_sdp))

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
