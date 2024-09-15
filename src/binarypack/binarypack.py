import struct
from typing import Any, Union, List, Dict
from io import BytesIO

Packable = Union[None, str, int, float, bool, bytes, List['Packable'], Dict[str, 'Packable']]
Unpackable = Union[None, str, int, float, bool, bytes, List['Unpackable'], Dict[str, 'Unpackable']]

def unpack(data: bytes) -> Unpackable:
    unpacker = Unpacker(data)
    return unpacker.unpack()

def pack(data: Packable) -> bytes:
    packer = Packer()
    return packer.pack(data)

class Unpacker:
    def __init__(self, data: bytes):
        self.buffer = BytesIO(data)

    def unpack(self) -> Unpackable:
        type_byte = self.unpack_uint8()
        
        if type_byte < 0x80:
            return type_byte
        elif (type_byte ^ 0xe0) < 0x20:
            return (type_byte ^ 0xe0) - 0x20

        size = 0
        if (size := type_byte ^ 0xa0) <= 0x0f:
            return self.unpack_raw(size)
        elif (size := type_byte ^ 0xb0) <= 0x0f:
            return self.unpack_string(size)
        elif (size := type_byte ^ 0x90) <= 0x0f:
            return self.unpack_array(size)
        elif (size := type_byte ^ 0x80) <= 0x0f:
            return self.unpack_map(size)

        if type_byte == 0xc0:
            return None
        elif type_byte == 0xc2:
            return False
        elif type_byte == 0xc3:
            return True
        elif type_byte == 0xca:
            return self.unpack_float()
        elif type_byte == 0xcb:
            return self.unpack_double()
        elif type_byte == 0xcc:
            return self.unpack_uint8()
        elif type_byte == 0xcd:
            return self.unpack_uint16()
        elif type_byte == 0xce:
            return self.unpack_uint32()
        elif type_byte == 0xcf:
            return self.unpack_uint64()
        elif type_byte == 0xd0:
            return self.unpack_int8()
        elif type_byte == 0xd1:
            return self.unpack_int16()
        elif type_byte == 0xd2:
            return self.unpack_int32()
        elif type_byte == 0xd3:
            return self.unpack_int64()
        elif type_byte == 0xd8:
            size = self.unpack_uint16()
            return self.unpack_string(size)
        elif type_byte == 0xd9:
            size = self.unpack_uint32()
            return self.unpack_string(size)
        elif type_byte == 0xda:
            size = self.unpack_uint16()
            return self.unpack_raw(size)
        elif type_byte == 0xdb:
            size = self.unpack_uint32()
            return self.unpack_raw(size)
        elif type_byte == 0xdc:
            size = self.unpack_uint16()
            return self.unpack_array(size)
        elif type_byte == 0xdd:
            size = self.unpack_uint32()
            return self.unpack_array(size)
        elif type_byte == 0xde:
            size = self.unpack_uint16()
            return self.unpack_map(size)
        elif type_byte == 0xdf:
            size = self.unpack_uint32()
            return self.unpack_map(size)
        
        raise ValueError(f"Unknown type byte: {type_byte}")

    def unpack_uint8(self) -> int:
        return struct.unpack('!B', self.buffer.read(1))[0]

    def unpack_uint16(self) -> int:
        return struct.unpack('!H', self.buffer.read(2))[0]

    def unpack_uint32(self) -> int:
        return struct.unpack('!I', self.buffer.read(4))[0]

    def unpack_uint64(self) -> int:
        return struct.unpack('!Q', self.buffer.read(8))[0]

    def unpack_int8(self) -> int:
        return struct.unpack('!b', self.buffer.read(1))[0]

    def unpack_int16(self) -> int:
        return struct.unpack('!h', self.buffer.read(2))[0]

    def unpack_int32(self) -> int:
        return struct.unpack('!i', self.buffer.read(4))[0]

    def unpack_int64(self) -> int:
        return struct.unpack('!q', self.buffer.read(8))[0]

    def unpack_float(self) -> float:
        return struct.unpack('!f', self.buffer.read(4))[0]

    def unpack_double(self) -> float:
        return struct.unpack('!d', self.buffer.read(8))[0]

    def unpack_raw(self, size: int) -> bytes:
        return self.buffer.read(size)

    def unpack_string(self, size: int) -> str:
        return self.buffer.read(size).decode('utf-8')

    def unpack_array(self, size: int) -> List[Unpackable]:
        return [self.unpack() for _ in range(size)]

    def unpack_map(self, size: int) -> Dict[str, Unpackable]:
        return {self.unpack(): self.unpack() for _ in range(size)}

class Packer:
    def __init__(self):
        self.buffer = BytesIO()

    def pack(self, data: Packable) -> bytes:
        if data is None:
            self.buffer.write(b'\xc0')
        elif isinstance(data, bool):
            self.buffer.write(b'\xc3' if data else b'\xc2')
        elif isinstance(data, int):
            self.pack_integer(data)
        elif isinstance(data, float):
            self.pack_float(data)
        elif isinstance(data, str):
            self.pack_string(data)
        elif isinstance(data, bytes):
            self.pack_binary(data)
        elif isinstance(data, list):
            self.pack_array(data)
        elif isinstance(data, dict):
            self.pack_map(data)
        else:
            raise TypeError(f"Cannot pack object of type {type(data)}")
        
        return self.buffer.getvalue()

    def pack_integer(self, num: int):
        if num >= 0:
            if num < 128:
                self.buffer.write(struct.pack('B', num))
            elif num < 256:
                self.buffer.write(b'\xcc' + struct.pack('B', num))
            elif num < 65536:
                self.buffer.write(b'\xcd' + struct.pack('!H', num))
            elif num < 4294967296:
                self.buffer.write(b'\xce' + struct.pack('!I', num))
            else:
                self.buffer.write(b'\xcf' + struct.pack('!Q', num))
        else:
            if num >= -32:
                self.buffer.write(struct.pack('b', num))
            elif num >= -128:
                self.buffer.write(b'\xd0' + struct.pack('b', num))
            elif num >= -32768:
                self.buffer.write(b'\xd1' + struct.pack('!h', num))
            elif num >= -2147483648:
                self.buffer.write(b'\xd2' + struct.pack('!i', num))
            else:
                self.buffer.write(b'\xd3' + struct.pack('!q', num))

    def pack_float(self, num: float):
        self.buffer.write(b'\xcb' + struct.pack('!d', num))

    def pack_string(self, s: str):
        data = s.encode('utf-8')
        length = len(data)
        if length < 32:
            self.buffer.write(struct.pack('B', 0xa0 | length))
        elif length < 256:
            self.buffer.write(b'\xd9' + struct.pack('B', length))
        elif length < 65536:
            self.buffer.write(b'\xda' + struct.pack('!H', length))
        else:
            self.buffer.write(b'\xdb' + struct.pack('!I', length))
        self.buffer.write(data)

    def pack_binary(self, data: bytes):
        length = len(data)
        if length < 256:
            self.buffer.write(b'\xc4' + struct.pack('B', length))
        elif length < 65536:
            self.buffer.write(b'\xc5' + struct.pack('!H', length))
        else:
            self.buffer.write(b'\xc6' + struct.pack('!I', length))
        self.buffer.write(data)

    def pack_array(self, arr: List[Packable]):
        length = len(arr)
        if length < 16:
            self.buffer.write(struct.pack('B', 0x90 | length))
        elif length < 65536:
            self.buffer.write(b'\xdc' + struct.pack('!H', length))
        else:
            self.buffer.write(b'\xdd' + struct.pack('!I', length))
        for item in arr:
            self.pack(item)

    def pack_map(self, m: Dict[str, Packable]):
        length = len(m)
        if length < 16:
            self.buffer.write(struct.pack('B', 0x80 | length))
        elif length < 65536:
            self.buffer.write(b'\xde' + struct.pack('!H', length))
        else:
            self.buffer.write(b'\xdf' + struct.pack('!I', length))
        for key, value in m.items():
            self.pack(key)
            self.pack(value)