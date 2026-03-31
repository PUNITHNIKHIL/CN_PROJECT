# Reliable P2P File Transfer Protocol

An interactive, peer-to-peer (P2P) file transfer application built entirely over UDP. This project implements a custom reliable data transfer protocol using **Selective Repeat ARQ**, ensuring fast, reliable, encrypted, and resumable file transfers over an unreliable network layer.

## Core Features

- **Reliability & Sequencing**: Custom packet headers ensure packet sequencing. Lost or delayed packets are seamlessly recovered using Selective Repeat Automatic Repeat ReQuest (ARQ).
- **Throughput Optimization**: Implements a Sliding Window protocol, allowing multiple packets to be in-flight concurrently without waiting for individual ACKs, maximizing network bandwidth utilization.
- **Dynamic RTT & Congestion Control**: Calculates the Round Trip Time (RTT) of packets on the fly using **Jacobson & Karn Algorithms** to dynamically scale the timeout timers and implement Exponential Backoff, perfectly adjusting to network latency spikes.
- **End-to-End Security**: Mathematical Public/Private Keypairs are swapped seamlessly during the handshake to execute an **Elliptic Curve Diffie-Hellman (ECDH)** key exchange. File chunks are secured symmetrically in transit using robust AES-256-CTR with zero manual passwords required.
- **Resumable Transfers**: If a transfer is interrupted unexpectedly (e.g., connection drop or crash), the system automatically syncs state and cleanly resumes exactly where it left off, avoiding redundant data transmission.
- **Integrity Checking**: Each chunk calculates a CRC32 checksum before transmission. The receiver strictly verifies this checksum and mathematically drops corrupted chunks.
- **Multiplexed Receiving**: The background daemon securely manages state per connecting client, permitting multiple completely different peers to send files to the node simultaneously.
- **Live Diagnostics**: The transmitter tracks in real-time what packets are being sent, dropped, and acknowledged, elegantly displaying a transfer statistics board (`MB/s`, `Time elapsed`, `Retransmissions`) upon transfer conclusion.

## Project Structure

- `protocol.py`: Defines the foundational binary UDP packet structure, header packing/unpacking tools, and CRC32 checksum validation logic.
- `crypto.py`: Implements the Ephemeral ECDH key generation, HKDF shared secret derivation, and AES-256-CTR cryptographic wrapper for encrypting chunk payloads efficiently without padding overhead.
- `receiver.py`: Contains the robust UDP daemon logic for maintaining per-client state mappings, buffering out-of-order sequence packets, decrypting AES payloads, and assembling files.
- `sender.py`: Implements the sliding window client, dynamic RTT calculus, `SYN` handshakes, real-time ACK logging, and selective packet retransmission.
- `node.py`: The main interactive shell application integrating the receiver and sender seamlessly into a single runtime.

## Getting Started

### Prerequisites
- Python 3.x
- Cryptography Engine: Execute `pip install cryptography`

### Usage

1. **Launch a Node**
   Open a terminal and start your node. It will bind to port `5000` by default.
   ```bash
   python node.py --port 5000
   ```

2. **Launch a Peer Node**
   On a different terminal (or a different computer on the same LAN), launch another node on an available port (e.g., `5001`).
   ```bash
   python node.py --port 5001
   ```

3. **Transfer a File**
   In the interactive prompt of your first node, establish a connection to your peer and execute a transfer. 
   ```text
   > connect 127.0.0.1 5001
   > send path/to/any/file.ext
   ```
   *The file will automatically securely encrypt, transmit, decrypt, and save in the background on the peer node into their `downloads/` directory.*

### Testing Resumability

To observe the resumable file transfer mechanism:
1. Start transferring a large file (e.g., a video or a large zip file).
2. Press `Ctrl+C` on the sender's terminal abruptly, killing the transfer mid-way.
3. Restart the sender node and run the exact same `send <filename>` command. 
4. The system will sync the sizes and resume without re-uploading the entire file.
