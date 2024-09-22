import unittest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, ANY
from peerjs_py.peer import Peer, PeerOptions, LogLevel, ReferrerPolicy, PeerErrorType
from peerjs_py.api import API
from peerjs_py.option_interfaces import PeerJSOption
from peerjs_py.logger import logger, LogLevel
from peerjs_py.enums import SocketEventType, PeerEventType
from aiortc import MediaStreamTrack
from aiortc import RTCPeerConnection, RTCSessionDescription, RTCIceCandidate, MediaStreamTrack, RTCDataChannel

class TestPeer(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        logger.set_log_level(LogLevel.All)

        self.mock_api_patcher = patch('peerjs_py.peer.API')
        self.mock_socket_patcher = patch('peerjs_py.peer.Socket')
        self.mock_api = self.mock_api_patcher.start()
        self.mock_socket = self.mock_socket_patcher.start()
        self.peer = Peer(id="TestPeer")
        self.peer.destroy = AsyncMock()

    async def asyncTearDown(self):
        if self.peer:
            await self.peer.destroy()
        self.mock_api_patcher.stop()
        self.mock_socket_patcher.stop()
        # Reset logging level
        logger.set_log_level(LogLevel.Disabled)

    def test_init_with_id(self):
        peer = Peer("test_id")
        self.assertEqual(peer._id, "test_id")

    async def test_init_without_id(self):
        mock_api_instance = AsyncMock()
        mock_api_instance.retrieve_id.return_value = "1234567890"
        self.mock_api.return_value = mock_api_instance

        mock_socket_instance = AsyncMock()
        mock_socket_instance.start = AsyncMock()
        mock_socket_instance.on = Mock()
        self.mock_socket.return_value = mock_socket_instance

        peer = Peer()
        peer._initialize = AsyncMock()
        
        print(f"Before start: peer._id = {peer._id}")
        await peer.start()
        print(f"After start: peer._id = {peer._id}")

        # Assert that retrieve_id was called and awaited
        mock_api_instance.retrieve_id.assert_awaited_once()
        self.assertEqual(peer._id, "1234567890")
        peer._initialize.assert_awaited_once_with("1234567890")
        mock_socket_instance.on.assert_any_call(SocketEventType.Close.value, peer._on_close)



    @patch('peerjs_py.dataconnection.BufferedConnection.Json.Json')
    async def test_connect(self, mock_json_class):
        # Create a mock instance
        mock_data_connection_instance = AsyncMock()
        mock_data_connection_instance.connection_id = 'dc_2alj5o5seq'
        
        # Set the mock class to return our mock instance
        mock_json_class.return_value = mock_data_connection_instance

        # Mock the initialize method to return a completed future
        initialize_future = asyncio.Future()
        initialize_future.set_result(None)
        mock_data_connection_instance.initialize.return_value = initialize_future

        open_future = asyncio.Future()
        mock_data_connection_instance.open_future = open_future

        # Create a task to set the result of open_future after a short delay
        async def set_open_future():
            await asyncio.sleep(0.2)
            open_future.set_result(True)
        asyncio.create_task(set_open_future())

        # Mock the _socket attribute of self.peer
        self.peer._socket = AsyncMock()
        self.peer._socket.send = AsyncMock()

        # Replace the Json serializer in the _serializers dictionary
        self.peer._serializers['json'] = mock_json_class
        
        connection = await self.peer.connect("peer_id")

        mock_data_connection_instance.initialize.assert_awaited_once()
        self.assertIn("peer_id", self.peer._connections)

        # Ensure the connection is added to the peer's connections
        self.assertIn(connection, self.peer._connections["peer_id"])

        # Additional assertions to verify the mock was used
        mock_json_class.assert_called_once()
        self.assertEqual(connection, mock_data_connection_instance)

    async def test_call(self):
        with patch('peerjs_py.peer.MediaConnection') as mock_media_connection:
            self.peer._socket = AsyncMock()
            self.peer._socket.send = AsyncMock()

            # Create mock stream
            mock_stream = Mock()
            mock_stream.id = 'mock_stream_id'
            mock_stream.getTracks.return_value = [
                Mock(spec=MediaStreamTrack, kind="audio"),
                Mock(spec=MediaStreamTrack, kind="video")
            ]

            # Set up the mock MediaConnection
            mock_media_connection_instance = AsyncMock()
            mock_media_connection.return_value = mock_media_connection_instance
            mock_media_connection_instance.initialize = AsyncMock()

            # Mock the 'on' method to capture the event handler
            mock_media_connection_instance.on = Mock()

            # Call the method
            connection = await self.peer.call("peer_id", mock_stream)

            # Assertions
            mock_media_connection.assert_called_once_with("peer_id", self.peer, {'_stream': mock_stream})
            mock_media_connection_instance.initialize.assert_awaited_once()

            self.assertIn("peer_id", self.peer._connections)
            self.assertIn(connection, self.peer._connections["peer_id"])

            # Check if 'on' method was called with 'stream' event
            mock_media_connection_instance.on.assert_called_with('stream')

            # Verify that the 'on' method was called and capture the callback
            self.assertTrue(mock_media_connection_instance.on.called)
            call_args = mock_media_connection_instance.on.call_args
            self.assertEqual(call_args[0][0], 'stream')
            
            # Verify that there's only one argument passed to 'on'
            self.assertEqual(len(call_args[0]), 1)

            # Print out the call_args for debugging
            print(f"call_args: {call_args}")
            print(f"call_args[0]: {call_args[0]}")

            # If you want to verify the implementation of 'on', you might need to check the Peer class
            # and see how it's actually using the 'on' method of MediaConnection
            
            
    async def test_destroy(self):
        mock_socket_instance = AsyncMock()
        mock_socket_instance.start = AsyncMock()
        mock_socket_instance.on = Mock()
        mock_socket_instance.remove_all_listeners = AsyncMock()
        mock_socket_instance.close = AsyncMock()  # Add this line
        self.mock_socket.return_value = mock_socket_instance

        peer = Peer()
        await peer.destroy()
        
        self.assertTrue(peer._destroyed)
        self.assertTrue(peer._disconnected)
        mock_socket_instance.on.assert_any_call(SocketEventType.Close.value, peer._on_close)
        mock_socket_instance.close.assert_awaited_once()  # Add this line
        # mock_socket_instance.remove_all_listeners.assert_awaited_once()

    async def test_disconnect(self):
        mock_socket_instance = AsyncMock()
        mock_socket_instance.start = AsyncMock()
        mock_socket_instance.on = Mock()
        self.mock_socket.return_value = mock_socket_instance

        peer = Peer()
        peer._id = "test_id"
        await peer.disconnect()
        self.assertTrue(peer._disconnected)
        self.assertFalse(peer._open)
        self.assertIsNone(peer._id)
        self.assertEqual(peer._last_server_id, "test_id")
        mock_socket_instance.on.assert_any_call(SocketEventType.Close.value, peer._on_close)

    async def test_reconnect(self):
        with patch('peerjs_py.peer.logger') as mock_logger:
            self.peer._disconnected = True
            self.peer._last_server_id = "last_id"
            self.peer._destroyed = False
            self.peer._initialize = AsyncMock()
            self.peer.start = AsyncMock()

            await self.peer.reconnect()

            self.assertFalse(self.peer._disconnected)
            mock_logger.info.assert_called_with("Attempting reconnection to server with ID last_id")
            self.peer._initialize.assert_called_once_with("last_id")
            self.peer.start.assert_called_once()


    @patch('peerjs_py.peer.API')
    async def test_list_all_peers(self, mock_api_class):
        mock_api_instance = AsyncMock()
        mock_api_instance.list_all_peers.return_value = ['peer1', 'peer2']
        mock_api_class.return_value = mock_api_instance

        self.peer._api = mock_api_instance
        result = await self.peer.list_all_peers()

        mock_api_instance.list_all_peers.assert_awaited_once()
        self.assertEqual(result, ['peer1', 'peer2'])

    @patch('peerjs_py.peer.API')
    async def test_list_all_peers_error(self, mock_api_class):
        mock_api_instance = AsyncMock()
        mock_api_instance.list_all_peers.side_effect = Exception("API Error")
        mock_api_class.return_value = mock_api_instance

        self.peer._api = mock_api_instance
        self.peer.emit_error = Mock()
        result = []
        try:
            result = await self.peer.list_all_peers()
        except Exception as e:
            mock_api_instance.list_all_peers.assert_awaited_once()
            self.peer.emit_error.assert_called_once_with(PeerErrorType.SERVER_ERROR, "API Error")
            self.assertEqual(result, [])

        mock_api_instance.list_all_peers.assert_awaited_once()
        self.peer.emit_error.assert_called_once_with(PeerErrorType.SERVER_ERROR, "API Error")
        self.assertEqual(result, [])

if __name__ == '__main__':
    unittest.main()