import json
import asyncio
import aiohttp
from typing import Any, List, Optional
from pyee.asyncio import AsyncIOEventEmitter

# Assuming these are defined elsewhere
from src.logger import logger
from src.enums import ServerMessageType, SocketEventType

version = "0.1.0"

class Socket(AsyncIOEventEmitter):
    def __init__(self, secure: bool, host: str, port: int, path: str, key: str, ping_interval: float = 5.0):
        super().__init__()
        self._disconnected: bool = True
        self._id: Optional[str] = None
        self._messages_queue: List[dict] = []
        self._session: Optional[aiohttp.ClientSession] = None
        self._ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self._ws_ping_task: Optional[asyncio.Task] = None
        ws_protocol = "wss://" if secure else "ws://"
        self._base_url = f"{ws_protocol}{host}:{port}{path}peerjs?key={key}"
        self.ping_interval = ping_interval

    async def start(self, id: str, token: str) -> None:
        self._id = id
        ws_url = f"{self._base_url}&id={id}&token={token}&version={version}"

        if self._ws or not self._disconnected:
            return

        self._session = aiohttp.ClientSession()
        try:
            self._ws = await self._session.ws_connect(ws_url)
            self._disconnected = False
            asyncio.create_task(self._listen())
            await self._on_open()
        except Exception as e:
            logger.log(f"Failed to connect: {e}")
            await self._cleanup()

    async def _listen(self) -> None:
        try:
            async for msg in self._ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    await self._on_message(msg.data)
                elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                    break
        finally:
            await self._on_close()

    async def _on_message(self, message: str) -> None:
        try:
            data = json.loads(message)
            logger.log("Server message received:", data)
            await self.emit(SocketEventType.Message, data)
        except json.JSONDecodeError:
            logger.log("Invalid server message", message)

    async def _on_close(self) -> None:
        if self._disconnected:
            return

        logger.log("Socket closed.")
        await self._cleanup()
        self._disconnected = True
        await self.emit(SocketEventType.Disconnected)

    async def _on_open(self) -> None:
        if self._disconnected:
            return

        await self._send_queued_messages()
        logger.log("Socket open")
        self._schedule_heartbeat()

    def _schedule_heartbeat(self) -> None:
        if self._ws_ping_task:
            self._ws_ping_task.cancel()
        self._ws_ping_task = asyncio.create_task(self._heartbeat_loop())

    async def _heartbeat_loop(self) -> None:
        while True:
            await asyncio.sleep(self.ping_interval)
            await self._send_heartbeat()

    async def _send_heartbeat(self) -> None:
        if not self._ws_open():
            logger.log("Cannot send heartbeat, because socket closed")
            return

        message = json.dumps({"type": ServerMessageType.Heartbeat})
        await self._ws.send_str(message)

    def _ws_open(self) -> bool:
        return self._ws and not self._ws.closed

    async def _send_queued_messages(self) -> None:
        copied_queue = self._messages_queue.copy()
        self._messages_queue.clear()

        for message in copied_queue:
            await self.send(message)

    async def send(self, data: Any) -> None:
        if self._disconnected:
            return

        if not self._id:
            self._messages_queue.append(data)
            return

        if not isinstance(data, dict) or 'type' not in data:
            await self.emit(SocketEventType.Error, "Invalid message")
            return

        if not self._ws_open():
            return

        message = json.dumps(data)
        await self._ws.send_str(message)

    async def close(self) -> None:
        if self._disconnected:
            return

        await self._cleanup()
        self._disconnected = True

    async def _cleanup(self) -> None:
        if self._ws:
            await self._ws.close()
            self._ws = None

        if self._session:
            await self._session.close()
            self._session = None

        if self._ws_ping_task:
            self._ws_ping_task.cancel()
            self._ws_ping_task = None