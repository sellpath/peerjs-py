from typing import List
import array

class BufferBuilder:
    def __init__(self):
        self._pieces: List[int] = []
        self._parts: List[memoryview] = []

    def append_buffer(self, data: memoryview):
        self.flush()
        self._parts.append(data)

    def append(self, data: int):
        self._pieces.append(data)

    def flush(self):
        if self._pieces:
            buf = array.array('B', self._pieces)
            self._parts.append(memoryview(buf))
            self._pieces.clear()

    def to_bytes(self) -> bytes:
        self.flush()
        return b''.join(bytes(part) for part in self._parts)

def concat_byte_arrays(bufs: List[memoryview]) -> bytes:
    return b''.join(bytes(buf) for buf in bufs)