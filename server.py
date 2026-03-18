import os
import ssl
import socket
import threading
from protocol import *

CERT_FILE = "certs/server.crt"
KEY_FILE = "certs/server.key"
SAVE_DIR = "received"


def make_ssl_context():

    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(certfile=CERT_FILE, keyfile=KEY_FILE)

    return ctx


class ClientHandler(threading.Thread):

    def __init__(self, conn, addr):

        threading.Thread.__init__(self)
        self.conn = conn
        self.addr = addr

    def run(self):

        print("Client connected:", self.addr)

        try:

            msg = recv_msg(self.conn)
            parts = msg.split()

            if parts[0] == "UPLOAD_REQ":
                self.handle_upload(parts)

            elif parts[0] == "DOWNLOAD_REQ":
                self.handle_download(parts)

        except Exception as e:

            print("Error:", e)

        finally:

            self.conn.close()

    # ---------------- UPLOAD ----------------
    def handle_upload(self, parts):

        filename = parts[1]
        filesize = int(parts[2])

        total_chunks = (filesize + CHUNK_SIZE - 1) // CHUNK_SIZE

        udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_sock.bind(("0.0.0.0", 0))

        udp_port = udp_sock.getsockname()[1]

        send_msg(self.conn, f"UPLOAD_ACK {udp_port}")

        received = {}

        while len(received) < total_chunks:

            pkt, _ = udp_sock.recvfrom(UDP_PACKET_SIZE + 64)

            seq, total, data = unpack_chunk(pkt)

            received[seq] = data

            send_msg(self.conn, f"ACK {seq}")

        file_data = reassemble(received, total_chunks)

        os.makedirs(SAVE_DIR, exist_ok=True)

        path = os.path.join(SAVE_DIR, filename)

        with open(path, "wb") as f:
            f.write(file_data)

        print("Saved:", path)

        send_msg(self.conn, "UPLOAD_COMPLETE")

    # ---------------- DOWNLOAD ----------------
    def handle_download(self, parts):

        filename = parts[1]

        path = os.path.join(SAVE_DIR, filename)

        if not os.path.exists(path):

            send_msg(self.conn, "FILE_NOT_FOUND")
            return

        chunks = split_file(path)

        total = len(chunks)

        send_msg(self.conn, f"DOWNLOAD_READY {total}")

        port_msg = recv_msg(self.conn)

        client_port = int(port_msg.split()[1])

        client_ip = self.addr[0]

        udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        for seq in range(total):

            pkt = pack_chunk(seq, total, chunks[seq])

            udp_sock.sendto(pkt, (client_ip, client_port))

        send_msg(self.conn, "DOWNLOAD_COMPLETE")

        print("File sent:", filename)


def main():

    ctx = make_ssl_context()

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    server.bind(("0.0.0.0", CONTROL_PORT))

    server.listen(5)

    print("Server running on port", CONTROL_PORT)

    while True:

        conn, addr = server.accept()

        try:

            ssl_conn = ctx.wrap_socket(conn, server_side=True)

            handler = ClientHandler(ssl_conn, addr)

            handler.start()

        except ssl.SSLError:

            conn.close()


if __name__ == "__main__":

    main()