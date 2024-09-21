import asyncio
from enum import Enum
from typing import Any, Callable, Dict, Union
from peerjs_py.base_connection import BaseConnection
from peerjs_py.negotiator import Negotiator
from peerjs_py.utils.random_token import random_token
from peerjs_py.enums import ServerMessageType, ConnectionType, ConnectionEventType, DataConnectionErrorType, SerializationType
from peerjs_py.logger import logger
import logging

class DataConnection(BaseConnection):
    ID_PREFIX = "dc_"
    MAX_BUFFERED_AMOUNT = 8 * 1024 * 1024

    def __init__(self, peer_id: str, provider: Any, options: Dict[str, Any]):
        super().__init__(peer_id, provider, options)
        self.connection_id = options.get('connection_id') or f"{self.ID_PREFIX}{random_token()}"
        self.label = options.get('label') or self.connection_id
        self.reliable = bool(options.get('reliable'))
        self.serialization = options.get('serialization', SerializationType.JSON)
        self._negotiator = Negotiator(self)
        self._open = False
        self.open_future = asyncio.Future()
        self.data_channel = None
        self.peer_connection = None

    async def initialize(self):
        await self._negotiator.start_connection(
            self.options.get('_payload') or {
                'originator': True,
                'reliable': self.reliable,
                'protocol': '' #"" empty "json", "protobuf", "cbor", "websocket-over-datachannels"
            }
    )
    @property
    def type(self):
        return ConnectionType.Data

    async def _initialize_data_channel(self, dc):
        if self.data_channel:
            logger.info(f"DC#{self.connection_id} Data channel already initialized")
            return
        
        logger.info(f"DC#{self.connection_id} _initialize_data_channel Data channel start  self.provider:{self.provider._id}")
        self.data_channel = dc
        logger.info(f"DC#{self.connection_id} Initializing data channel")
        
        @self.data_channel.on("open")
        async def on_open():
            logger.info(f"DC#{self.connection_id} Data channel opened <======self.provider:{self.provider._id}")
            self._open = True
            self.open_future.set_result(True)
            self.emit(ConnectionEventType.Open.value)

        @self.data_channel.on("message")
        async def on_message(msg):
            logger.info(f"DC#{self.connection_id} Received message: {msg}")
            await self._handle_data_message(msg)

        @self.data_channel.on("close")
        async def on_close():
            logger.info(f"DC#{self.connection_id} Data channel closed for: {self.peer}")
            await self.close()

        @self.data_channel.on("statechange")
        async def on_statechange():
            logger.debug(f"DC#{self.connection_id} DataChannel state changed to: {self._dc.readyState}")

        logger.info(f"DC#{self.connection_id} Data channel initialized")

    async def close(self, options: Dict[str, bool] = None):
        if options and options.get('flush'):
            self.send({
                "__peerData": {
                    "type": "close"
                }
            })
            return

        if self._negotiator:
            await self._negotiator.cleanup()
            self._negotiator = None

        if self.provider:
            await self.provider._remove_connection(self)
            self.provider = None

        if self.data_channel:
            self.data_channel.remove_all_listeners()
            self.data_channel = None

        if not self._open:
            return

        self._open = False
        super().emit(ConnectionEventType.Close.value)

    async def send(self, data: Any, chunked: bool = False):
        if not self._open:
            # if not self.data_channel:
            #     logger.debug("call initialize to setup data_channel")
            #     await self.initialize()
            # await self.open()
            self.emit_error(
                DataConnectionErrorType.NOT_OPEN_YET.value,
                "Connection is not open. You should listen for the `open` event before sending messages."
            )
            return
        return await self._send(data, chunked)

    async def _send(self, data: Any, chunked: bool):
        # This method should be implemented in a subclass
        logger.exception(f"check where this comes from")
        raise NotImplementedError("_send method must be implemented in a subclass")


    async def handle_message(self, message: Dict[str, Any]):
        payload = message['payload']

        if message['type'] == ServerMessageType.Answer.value:
            logger.info(f"DC#{self.connection_id} Received ANSWER from {self.peer}")
            await self._negotiator.handle_sdp(message['type'], payload['sdp'])
        elif message['type'] == ServerMessageType.Candidate.value:
            logger.info(f"DC#{self.connection_id} Received ICE candidate from {self.peer}")
            await self._negotiator.handle_candidate(payload['candidate'])
        elif message['type'] == ServerMessageType.Offer.value:
            received_connection_id = payload.get('connectionId')
            if received_connection_id and isinstance(received_connection_id, str):
                if self.connection_id and self.connection_id != received_connection_id:
                    logger.warning(f"DC# Received different connectionId: {received_connection_id}, current: {self.connection_id}")
                else:
                    self.connection_id = received_connection_id
                    logger.info(f"DC#{self.connection_id} Received OFFER from {self.peer}")
            else:
                logger.warning("Received OFFER without valid connectionId fail set connection_id")

            sdp = payload.get('sdp')
            if sdp:
                await self._negotiator.handle_sdp(message['type'], sdp)
            else:
                logger.error("Received OFFER without SDP")
        else:
            logger.warning(f"DC#{self.connection_id} Unrecognized message type: {message['type']} from peer: {self.peer}")