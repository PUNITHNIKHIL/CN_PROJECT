import struct
import hashlib

CHUNK_SIZE = 4096
UDP_HEADER_SIZE = 12
UDP_PACKET_SIZE = CHUNK_SIZE + UDP_HEADER_SIZE

CONTROL_PORT = 9000
BUFFER_SIZE = 8192


def pack_chunk(seq, total, data):
    header = struct.pack("!III", seq, total, len(data))
    return header + data


def unpack_chunk(packet):
    seq, total, size = struct.unpack("!III", packet[:12])
    data = packet[12:12+size]
    return seq, total, data


def split_file(path):

    chunks = []

    with open(path, "rb") as f:
        while True:
            data = f.read(CHUNK_SIZE)

            if not data:
                break

            chunks.append(data)

    return chunks


def reassemble(chunks, total):

    data = b""

    for i in range(total):
        data += chunks[i]

    return data


def sha256_file(path):

    h = hashlib.sha256()

    with open(path, "rb") as f:
        while True:
            b = f.read(65536)

            if not b:
                break

            h.update(b)

    return h.hexdigest()


def send_msg(sock, msg):

    sock.sendall((msg + "\n").encode())


def recv_msg(sock):

    data = b""

    while not data.endswith(b"\n"):

        part = sock.recv(BUFFER_SIZE)

        if not part:
            raise ConnectionError("Connection closed")

        data += part

    return data.decode().strip()