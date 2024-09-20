import math

CHUNKED_MTU = 16300
class BinaryPackChunker:
    def __init__(self):
        # The original 60000 bytes setting does not work when sending data from Firefox to Chrome,
        # which is "cut off" after 16384 bytes and delivered individually.
        self.chunked_mtu = CHUNKED_MTU
        self._data_count = 1

    def chunk(self, blob):
        chunks = []
        size = len(blob)
        total = math.ceil(size / self.chunked_mtu)

        index = 0
        start = 0

        while start < size:
            end = min(size, start + self.chunked_mtu)
            b = blob[start:end]

            chunk = {
                "__peerData": self._data_count,
                "n": index,
                "data": b,
                "total": total,
            }

            chunks.append(chunk)

            start = end
            index += 1

        self._data_count += 1

        return chunks

def concat_array_buffers(bufs):
    return b''.join(bufs)