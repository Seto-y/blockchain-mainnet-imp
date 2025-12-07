import struct
import time
from typing import List, Tuple, Optional

MAINNET_MAGIC = 0xD9B4BEF9
TESTNET_MAGIC = 0x0709110B
REGTEST_MAGIC = 0xDAB5BFFA

PROTOCOL_VERSION = 70015

MSG_VERSION = b'version\x00\x00\x00\x00\x00'
MSG_VERACK = b'verack\x00\x00\x00\x00\x00\x00'
MSG_GETADDR = b'getaddr\x00\x00\x00\x00\x00'
MSG_ADDR = b'addr\x00\x00\x00\x00\x00\x00\x00\x00\x00'


def varint_encode(value: int) -> bytes:
    if value < 0xFD:
        return struct.pack('<B', value)
    elif value <= 0xFFFF:
        return struct.pack('<BH', 0xFD, value)
    elif value <= 0xFFFFFFFF:
        return struct.pack('<BI', 0xFE, value)
    else:
        return struct.pack('<BQ', 0xFF, value)


def varint_decode(data: bytes, offset: int = 0) -> Tuple[int, int]:
    if offset >= len(data):
        raise ValueError("Insufficient data for varint")
    
    first_byte = data[offset]
    
    if first_byte < 0xFD:
        return first_byte, offset + 1
    elif first_byte == 0xFD:
        if offset + 3 > len(data):
            raise ValueError("Insufficient data for varint")
        value = struct.unpack('<H', data[offset + 1:offset + 3])[0]
        return value, offset + 3
    elif first_byte == 0xFE:
        if offset + 5 > len(data):
            raise ValueError("Insufficient data for varint")
        value = struct.unpack('<I', data[offset + 1:offset + 5])[0]
        return value, offset + 5
    else:
        if offset + 9 > len(data):
            raise ValueError("Insufficient data for varint")
        value = struct.unpack('<Q', data[offset + 1:offset + 9])[0]
        return value, offset + 9


def create_message(command: bytes, payload: bytes, magic: int = MAINNET_MAGIC) -> bytes:
    command_padded = command[:12].ljust(12, b'\x00')
    length = len(payload)
    import hashlib
    checksum = hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
    return struct.pack('<I', magic) + command_padded + struct.pack('<I', length) + checksum + payload


def create_version_message(
    version: int = PROTOCOL_VERSION,
    services: int = 1,
    timestamp: Optional[int] = None,
    addr_recv: Tuple[str, int] = ("0.0.0.0", 0),
    addr_from: Tuple[str, int] = ("0.0.0.0", 0),
    nonce: Optional[int] = None,
    user_agent: str = "/BitcoinCrawler:0.1/",
    start_height: int = 0,
    relay: bool = True
) -> bytes:
    if timestamp is None:
        timestamp = int(time.time())
    
    if nonce is None:
        import random
        nonce = random.getrandbits(64)
    
    def encode_ip(ip: str, port: int) -> bytes:
        ip_parts = [int(x) for x in ip.split('.')]
        ipv6_format = bytes([0x00] * 10 + [0xFF, 0xFF] + ip_parts)
        return struct.pack('<Q', services) + ipv6_format + struct.pack('>H', port)
    
    payload = struct.pack('<I', version)
    payload += struct.pack('<Q', services)
    payload += struct.pack('<Q', timestamp)
    payload += encode_ip(addr_recv[0], addr_recv[1])
    payload += encode_ip(addr_from[0], addr_from[1])
    payload += struct.pack('<Q', nonce)
    payload += varint_encode(len(user_agent)) + user_agent.encode('utf-8')
    payload += struct.pack('<I', start_height)
    payload += struct.pack('<?', relay)
    
    return create_message(MSG_VERSION, payload)


def create_verack_message() -> bytes:
    return create_message(MSG_VERACK, b'')


def create_getaddr_message() -> bytes:
    return create_message(MSG_GETADDR, b'')


def parse_addr_message(data: bytes) -> List[Tuple[str, int, int]]:
    if len(data) < 1:
        return []
    
    try:
        count, offset = varint_decode(data, 0)
        addresses = []
        
        for _ in range(min(count, 1000)):
            if offset + 30 > len(data):
                break
            
            timestamp = struct.unpack('<I', data[offset:offset + 4])[0]
            offset += 4
            services = struct.unpack('<Q', data[offset:offset + 8])[0]
            offset += 8
            
            ip_bytes = data[offset:offset + 16]
            offset += 16
            
            if ip_bytes[:12] == bytes(12) and ip_bytes[12:14] == b'\xFF\xFF':
                ip = '.'.join(str(b) for b in ip_bytes[14:18])
            else:
                offset += 2
                continue
            
            port = struct.unpack('>H', data[offset:offset + 2])[0]
            offset += 2
            
            addresses.append((ip, port, timestamp))
        
        return addresses
    except (ValueError, struct.error, IndexError):
        return []


def parse_message(data: bytes) -> Optional[Tuple[bytes, bytes]]:
    if len(data) < 24:
        return None
    
    magic = struct.unpack('<I', data[0:4])[0]
    if magic != MAINNET_MAGIC:
        return None
    
    command = data[4:16].rstrip(b'\x00')
    length = struct.unpack('<I', data[16:20])[0]
    checksum = data[20:24]
    
    if length > 2 * 1024 * 1024:
        return None
    
    if len(data) < 24 + length:
        return None
    
    payload = data[24:24 + length]
    
    import hashlib
    calculated_checksum = hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
    if calculated_checksum != checksum:
        return None
    
    return (command, payload)

