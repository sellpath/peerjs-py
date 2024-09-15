from typing import Generic, TypeVar, Callable
from pyee import EventEmitter
import logging
from typing import Union

logger = logging.getLogger(__name__)

ErrorType = TypeVar('ErrorType', bound=str)

class PeerError(Generic[ErrorType], Exception):
    def __init__(self, type: ErrorType, err: Union[str, Exception]):
        if isinstance(err, str):
            super().__init__(err)
        else:
            super().__init__()
            self.__dict__.update(err.__dict__)
        self.type = type

class EventEmitterWithError(Generic[ErrorType], EventEmitter):
    def emit_error(self, type: ErrorType, err: Union[str, Exception]) -> None:
        logger.error("Error: %s", err)
        self.emit("error", PeerError(type, err))
