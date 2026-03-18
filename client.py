import socket
import ssl
import os
import sys
from protocol import *

CERT_FILE = "certs/server.crt"


def make_ssl_context():

    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)

    ctx.load_verify_locations(CERT_FILE)

    ctx.check_hostname = False

    return ctx


# ---------------- UPLOAD ----------------
def upload(server_ip, filepath):

    filename = os.path.basename(filepath)

    filesize = os.path.getsize(filepath)

    chunks = split_file(filepath)

    total = len(chunks)

    ctx = make_ssl_context()

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    sock.connect((server_ip, CONTROL_PORT))

    ssl_sock = ctx.wrap_socket(sock)

    send_msg(ssl_sock, f"UPLOAD_REQ {filename} {filesize}")

    resp = recv_msg(ssl_sock)

    udp_port = int(resp.split()[1])

    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    pending = set(range(total))

    while pending:

        for seq in pending:

            pkt = pack_chunk(seq, total, chunks[seq])

            udp_sock.sendto(pkt, (server_ip, udp_port))

        try:

            msg = recv_msg(ssl_sock)

            if msg.startswith("ACK"):

                seq = int(msg.split()[1])

                pending.discard(seq)

        except:

            pass

    print(recv_msg(ssl_sock))

    ssl_sock.close()


# ---------------- DOWNLOAD ----------------
def download(server_ip, filename):

    ctx = make_ssl_context()

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    sock.connect((server_ip, CONTROL_PORT))

    ssl_sock = ctx.wrap_socket(sock)

    send_msg(ssl_sock, f"DOWNLOAD_REQ {filename}")

    resp = recv_msg(ssl_sock)

    if resp == "FILE_NOT_FOUND":

        print("File not found on server")

        return

    total = int(resp.split()[1])

    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    udp_sock.bind(("0.0.0.0", 0))

    port = udp_sock.getsockname()[1]

    send_msg(ssl_sock, f"PORT {port}")

    received = {}

    while len(received) < total:

        pkt, _ = udp_sock.recvfrom(UDP_PACKET_SIZE + 64)

        seq, total_chunks, data = unpack_chunk(pkt)

        received[seq] = data

    data = reassemble(received, total)

    os.makedirs("downloads", exist_ok=True)

    path = os.path.join("downloads", filename)

    with open(path, "wb") as f:
        f.write(data)

    print("Downloaded:", path)

    ssl_sock.close()


if __name__ == "__main__":

    if len(sys.argv) < 4:

        print("Usage:")
        print("Upload: python client.py upload <server_ip> <file>")
        print("Download: python client.py download <server_ip> <file>")

        sys.exit()

    cmd = sys.argv[1]

    if cmd == "upload":

        upload(sys.argv[2], sys.argv[3])

    elif cmd == "download":

        download(sys.argv[2], sys.argv[3])