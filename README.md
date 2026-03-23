# Reliable P2P File Transfer Protocol

`CS 918 | CS 601 | CS 558`

---
An interactive, peer-to-peer (P2P) file transfer application built entirely over UDP. This project implements a custom reliable data transfer protocol using **Selective Repeat ARQ**, ensuring fast, reliable, and resumable file transfers over an unreliable network layer.

## Features

- **Reliability over UDP**: Custom packet headers ensure packet sequencing. Lost or delayed packets are seamlessly recovered using Selective Repeat Automatic Repeat ReQuest (ARQ).
- **Throughput Optimization**: Implements a Sliding Window protocol, allowing multiple packets to be in-flight concurrently without waiting for individual ACKs, maximizing network bandwidth.
- **Resumable Transfers**: If a transfer is interrupted unexpectedly (e.g., connection drop or crash), the system automatically syncs size states and resumes exactly where it left off, avoiding redundant data transmission.
- **Integrity Checking**: Each chunk calculates a CRC32 checksum before transmission. The receiver strictly verifies this checksum and drops corrupted packets.
- **Multiplexed Receiving**: The background daemon securely manages state per connecting client, permitting multiple different peers to send files to the node simultaneously.
- **Peer-to-Peer CLI**: A simple, unified command-line node interface that runs a background listener while providing an active shell for sending robust files.

## Project Structure

- `protocol.py`: Defines the foundational custom binary UDP packet structure, header packing/unpacking, and CRC32 checksum validation logic.
- `receiver.py`: Contains the robust UDP daemon logic for maintaining per-client state mapping, buffering out-of-order sequence packets, and writing consecutive packets efficiently to the disk.
- `sender.py`: Implements the sliding window client, handling SYN handshakes for resuming files, monitoring ACK timeouts, and executing selective packet retransmission.
- `node.py`: The main interactive shell application integrating the receiver and sender seamlessly into a single runtime.

## Getting Started

### Prerequisites
- Python 3.x (No external dependencies required)

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
   In the interactive prompt of your first node, establish a connection to your peer and execute a transfer:
   ```text
   > connect 127.0.0.1 5001
   > send path/to/any/file.ext
   ```

   *The file will automatically begin downloading in the background on the peer node into a `downloads/` directory.*

### Testing Resumability

To observe the resumable file transfer mechanism:
1. Start transferring a large file (e.g., a video or a large zip file).
2. Press `Ctrl+C` on the sender's terminal abruptly, killing the transfer mid-way.
3. Restart the sender node and run the exact same `send <filename>` command. 
4. The system will log `Resuming from seq: <number>` and instantly pick up the transfer block without re-uploading the entire file.
