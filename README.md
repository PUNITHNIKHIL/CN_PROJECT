# Project 8 — Reliable File Transfer Protocol (Custom FTP)
**CS558 / CS601 / CS918 | CN Mini Project | Deliverable 1**

---

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                      HYBRID DESIGN                        │
│                                                           │
│  TCP + SSL/TLS  ──►  Control Channel                      │
│                      (session setup, metadata, ACK/NACK)  │
│                                                           │
│  UDP            ──►  Data Channel                         │
│                      (raw file chunks, high throughput)   │
└──────────────────────────────────────────────────────────┘

CLIENT                             SERVER
  │                                   │
  │── SSL Handshake (TCP:9000) ──────►│
  │◄─ Handshake Complete ─────────────│
  │                                   │
  │── UPLOAD_REQ <name> <size> <sha>─►│
  │◄─ UPLOAD_ACK <udp_port> <chunk> ──│
  │                                   │  (server opens UDP socket)
  │══ UDP chunks (seq, total, data) ══►│
  │◄─ CHUNK_ACK <seq>  (SSL/TCP) ─────│
  │══ retransmit NACKed chunks ════════►│
  │                                   │
  │◄─ TRANSFER_OK <sha256> ───────────│
```

---

## Files

| File | Description |
|---|---|
| `server.py` | Multi-threaded server — SSL/TCP control + per-session UDP |
| `client.py` | Client — upload/download with SSL + UDP chunks |
| `protocol.py` | Shared: chunk packing, SHA-256, message framing |
| `test_multi_client.py` | Spawns 3 concurrent clients for Deliverable 1 demo |
| `certs/server.crt` | Self-signed TLS certificate |
| `certs/server.key` | TLS private key |

---

## Setup

### 1. Generate Certificates (already done — skip if certs exist)
```bash
openssl req -x509 -newkey rsa:2048 \
    -keyout certs/server.key -out certs/server.crt \
    -days 365 -nodes -subj "/CN=localhost"
```

### 2. Install dependencies
```bash
# No third-party packages required — uses Python stdlib only
python3 --version   # needs 3.9+
```

### 3. Run the server
```bash
python3 server.py
# Listens on TCP:9000 (SSL control) + dynamic UDP ports per session
```

### 4. Upload a file (single client)
```bash
python3 client.py upload 127.0.0.1 /path/to/myfile.txt
```

### 5. Download a file
```bash
python3 client.py download 127.0.0.1 myfile.txt
```

### 6. Multi-client demo (Deliverable 1)
```bash
# Terminal 1
python3 server.py

# Terminal 2
python3 test_multi_client.py
```

---

## Protocol Design

### Control Messages (SSL/TCP — newline delimited)

| Message | Direction | Meaning |
|---|---|---|
| `UPLOAD_REQ <name> <size> <sha256>` | C→S | Start upload |
| `UPLOAD_ACK <udp_port> <chunk_size>` | S→C | Ready, use this UDP port |
| `CHUNK_ACK <seq>` | S→C | Chunk received OK |
| `CHUNK_NACK <seq>` | S→C | Retransmit this chunk |
| `TRANSFER_OK <sha256>` | S→C | File complete and verified |
| `TRANSFER_ERR <reason>` | S→C | Failure |
| `DOWNLOAD_REQ <filename>` | C→S | Request download |
| `DOWNLOAD_META <size> <sha> <chunks>` | S→C | File metadata |
| `DOWNLOAD_READY <udp_port>` | C→S | Ready to receive on this UDP port |

### UDP Chunk Format (binary, 12-byte header)

```
 0        4        8       12     12+N
 ┌────────┬────────┬────────┬──────────┐
 │seq_num │total   │data_len│  data... │
 │(4B BI) │(4B BI) │(4B BI) │          │
 └────────┴────────┴────────┴──────────┘
```
- **BI** = Big-endian unsigned int (`!I` in Python struct)
- Default chunk size: **4096 bytes**

---

## Deliverable 1 Checklist

- [x] SSL/TLS handshake on control channel (TCP:9000)
- [x] File split into chunks, sent over UDP
- [x] Per-chunk ACK/NACK over secure SSL channel
- [x] SHA-256 integrity verification after full transfer
- [x] Multi-client support via threading (one thread per session)
- [x] Graceful handling of client disconnect / UDP timeout
- [x] `test_multi_client.py` — 3 concurrent clients demo

---

## Key Design Decisions

**Why TCP for control + UDP for data?**
- SSL/TLS requires a reliable, ordered stream → TCP is the right fit for the control channel
- Data chunks benefit from UDP's lower overhead and parallelism
- This mirrors how protocols like TFTP, QUIC, and media streaming work

**Why ACK over TCP instead of UDP?**
- ACKs are tiny and order-sensitive — TCP/SSL guarantees they arrive reliably without extra implementation cost
- Keeps the reliability logic simple: sender retransmits anything not ACKed

**Chunk size = 4096 bytes**
- Fits comfortably within common MTU after headers; easy to tune in `protocol.py`
