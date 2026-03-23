import struct
import zlib

"""
Packet Format:
- Sequence Number (4 bytes, unsigned int)
- Acknowledgment Number (4 bytes, unsigned int)
- Flags (1 byte, unsigned char)
- Checksum (4 bytes, unsigned int)
- Payload (variable, up to 1400 bytes)

Total Header Size: 13 bytes
"""

MAX_PAYLOAD_SIZE = 1400
HEADER_FORMAT = "!IIB I" # Seq (4), Ack (4), Flags (1), Checksum (4)
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

# Flags
FLAG_SYN = 1 << 0
FLAG_ACK = 1 << 1
FLAG_FIN = 1 << 2
FLAG_DATA = 1 << 3

def create_packet(seq_num, ack_num, flags, payload=b""):
    """
    Creates a UDP packet with the given header fields and payload.
    Calculates the CRC32 checksum over the payload.
    """
    checksum = zlib.crc32(payload) & 0xffffffff
    header = struct.pack(HEADER_FORMAT, seq_num, ack_num, flags, checksum)
    return header + payload

def parse_packet(packet):
    """
    Parses a UDP packet into header fields and payload.
    Verifies the CRC32 checksum. Returns None if checksum fails or packet is too small.
    """
    if len(packet) < HEADER_SIZE:
        return None
        
    header = packet[:HEADER_SIZE]
    payload = packet[HEADER_SIZE:]
    
    try:
        seq_num, ack_num, flags, checksum = struct.unpack(HEADER_FORMAT, header)
    except struct.error:
        return None
        
    calc_checksum = zlib.crc32(payload) & 0xffffffff
    if checksum != calc_checksum:
        return None  # Checksum mismatch
        
    return seq_num, ack_num, flags, payload
