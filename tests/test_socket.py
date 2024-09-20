import asyncio
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, patch
from peerjs_py.socket import Socket
from peerjs_py.enums import ServerMessageType, SocketEventType
from peerjs_py.logger import logger, LogLevel
import json


class TestSocket(IsolatedAsyncioTestCase):
    def setUp(self):
        logger.set_log_level(LogLevel.All)

        self.socket = Socket(secure=False, host="localhost", port=9000, path="/", key="test_key")

    async def test_socket_initialization(self):
        self.assertTrue(self.socket._disconnected)
        self.assertIsNone(self.socket._id)
        self.assertEqual(self.socket._messages_queue, [])
        self.assertIsNone(self.socket._session)
        self.assertIsNone(self.socket._ws)
        self.assertIsNone(self.socket._ws_ping_task)
        self.assertEqual(self.socket._base_url, "ws://localhost:9000/peerjs?key=test_key")

    async def test_socket_start(self):
        with patch('aiohttp.ClientSession.ws_connect', new_callable=AsyncMock) as mock_ws_connect:
            mock_ws = AsyncMock()
            mock_ws_connect.return_value = mock_ws
            
            await self.socket.start("test_id", "test_token")
            
            self.assertEqual(self.socket._id, "test_id")
            self.assertFalse(self.socket._disconnected)
            self.assertIsNotNone(self.socket._session)
            self.assertIsNotNone(self.socket._ws)
            
            mock_ws_connect.assert_called_once_with(
                f"{self.socket._base_url}&id=test_id&token=test_token&version=0.1.0"
            )

    async def test_socket_send_queued_messages(self):
        self.socket._id = "test_id"
        self.socket._ws = AsyncMock()
        self.socket._ws.send_str = AsyncMock()
        self.socket._ws_open = lambda: True  
        self.socket._disconnected = False
        
        test_messages = [
            {"type": "message1", "data": "test1"},
            {"type": "message2", "data": "test2"}
        ]
        self.socket._messages_queue = test_messages.copy()
        
        await self.socket._send_queued_messages()
        
        self.assertEqual(self.socket._messages_queue, [])
        self.assertEqual(self.socket._ws.send_str.call_count, 2)
        for msg in test_messages:
            self.socket._ws.send_str.assert_any_call(json.dumps(msg))

    async def test_socket_close(self):
        self.socket._ws = AsyncMock()
        self.socket._ws.close = AsyncMock()
        self.socket._session = AsyncMock()
        self.socket._ws_ping_task = AsyncMock()
        self.socket._disconnected = False
        
        with patch.object(Socket, '_cleanup', new_callable=AsyncMock) as mock_cleanup:
            await self.socket.close()
            
            self.assertTrue(self.socket._disconnected)
            mock_cleanup.assert_called_once()