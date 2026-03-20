# Reliable File Transfer (Custom Hybrid Protocol)

`CS558 / CS601 / CS918 | CN Mini Project`

Hybrid design:
- Control: `TLS-over-TCP` (`localhost:9000`)
- Data: `UDP` chunks
- No external dependencies (Python stdlib only)

## 📁 Files

- server.py: TLS control server, per-client `Thread`, per-session UDP port
- client.py: `upload()` + `download()` client routines
- protocol.py: constants + `split/reassemble` + `pack/unpack` + framed messages
- test_multi_client.py: 3 concurrent upload clients for validation
- server.crt, server.key: self-signed TLS cert/key
- received: server-side received files
- `downloads/`: client-side downloaded files

## ⚙️ Setup

1. (Optional) Make certs if missing:
   ```bash
   openssl req -x509 -newkey rsa:2048 \
     -keyout certs/server.key -out certs/server.crt \
     -days 365 -nodes -subj "/CN=localhost"
   ```
2. Python 3.9+
3. Run server:
   ```bash
   python server.py
   ```

## ▶️ Upload

1. Client init TLS connection → `UPLOAD_REQ <name> <filesize>`
2. Server opens UDP socket, replies `UPLOAD_ACK <udp_port>`
3. Client sends all chunks over UDP:
   - each chunk = `seq,total,len,data`
4. Server replies per-chunk `ACK <seq>` on TLS channel
5. Client loops pending until all ACKed
6. Server writes `received/<name>` and sends `UPLOAD_COMPLETE`

Usage:
```bash
python client.py upload 127.0.0.1 /path/to/file.bin
```

## ▶️ Download

1. Client TLS `DOWNLOAD_REQ <name>`
2. Server responds:
   - `FILE_NOT_FOUND` or
   - `DOWNLOAD_READY <total>`
3. Client binds a local UDP port, sends `PORT <port>`
4. Server UDP sends all chunks to client
5. Client reassembles and writes `downloads/<name>`
6. Server sends `DOWNLOAD_COMPLETE`

Usage:
```bash
python client.py download 127.0.0.1 file.bin
```

## 🧠 Protocol (actual in code)

- `CONTROL_PORT=9000`
- `CHUNK_SIZE=4096`
- UDP payload: 12-byte header + data:
  - `(seq, total, len)` as `!III`
- TLS control message ends with `\n` (send_msg/recv_msg)

## 🧪 Demo: concurrent clients

```bash
python test_multi_client.py
```
- Creates:
  - `small_1KB.bin`
  - `medium_64KB.bin`
  - `large_256KB.bin`
- Launches 3 threads:
  - each calls `upload("127.0.0.1", file)`
- Reports success/failure + timing

## ⚠️ Behavior notes

- No explicit retransmission timer in code (infinite retry in loop until ACKs arrive)
- No packet loss simulation; UDP reliability is assumed on local host
- No SHA-256 hash or CRC validation currently in `client.upload` / `server.handle_upload` in actual implementation (the code has helpers in protocol.py, but they are unused)
- No per-chunk `NACK` in current flow, only `ACK`; pending set loop triggers resend
