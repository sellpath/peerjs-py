from typing import Generic, TypeVar, Callable
from pyee import EventEmitter
from typing import Union
from pyee.asyncio import AsyncIOEventEmitter

from peerjs_py.enums import PeerEventType
from peerjs_py.logger import logger

ErrorType = TypeVar('ErrorType', bound=str)

class PeerError(Generic[ErrorType], Exception):
    def __init__(self, type: ErrorType, err: Union[str, Exception]):
        if isinstance(err, str):
            super().__init__(err)
        else:
            super().__init__()
            self.__dict__.update(err.__dict__)
        self.type = type

class EventEmitterWithError(Generic[ErrorType], EventEmitter): #EventEmitter  # AsyncIOEventEmitter
    def emit_error(self, type: ErrorType, err: Union[str, Exception]) -> None:
        logger.error("EventEmitterWithError Error: %s", err)
        self.emit(PeerEventType.Error.value, PeerError(type, err))

    async def emit_error_async(self, type: ErrorType, err: Union[str, Exception]) -> None:
        logger.error("EventEmitterWithError Error: %s", err)
        self.emit(PeerEventType.Error.value, PeerError(type, err))