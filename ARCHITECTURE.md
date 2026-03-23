# Architecture & Protocol Design

This document explains the underlying mechanics of the Reliable P2P File Transfer Protocol. Since raw UDP does not guarantee delivery, ordering, or data integrity, this custom protocol was designed to build TCP-like reliability directly at the application layer.

## 1. Custom Packet Structure

Every chunk of data sent over the network is encapsulated in a custom binary packet header generated via Python's `struct` module. 

| Field | Size | Description |
| :--- | :---: | :--- |
| **Sequence Number** | 4 bytes | Identifies the exact chunk offset in the file to guarantee structural order. |
| **Acknowledgment Number** | 4 bytes | Used by the receiver to inform the sender which specific chunk was successfully received. |
| **Flags** | 1 byte | Bitmask indicating the packet control type (`SYN` = Handshake, `ACK` = Acknowledgment, `FIN` = End of Transfer, `DATA` = File Fragment). |
| **Checksum** | 4 bytes | A CRC32 hash computed exclusively on the payload to detect network corruption. |
| **Payload** | <= 1400 bytes| Raw file data. Kept below 1400 bytes to easily fit inside standard 1500 byte Ethernet MTUs. |

## 2. Reliability & Throughput: Selective Repeat ARQ

To ensure no packets are permanently lost while simultaneously maximizing network throughput speed, the sender uses **Selective Repeat Automatic Repeat Request (ARQ)**.

1. **Sliding Window:** The sender does not patiently wait for an acknowledgment (ACK) after every single packet. Instead, it concurrently broadcasts up to 64 consecutive packets at once (its "Window Size").
2. **Selective ACKs:** When the receiver secures a packet, it immediately fires back a specific ACK for that exact sequence number. 
3. **Timeouts & Retransmission:** The sender maintains a timestamp for all unacknowledged packets. If a packet's ACK is not received within `0.5 seconds`, the sender deduces it was dropped by the router and *selectively retransmits only that specific missing packet*, rather than dropping back and resending the entire window.

## 3. The Synchronization Handshake (Resumability)

Before raw file transmission begins, a critical synchronization handshake dictates the state.

1. The sender initiates transfer by transmitting a `SYN` packet containing a JSON payload with the `filename` and total `file size`.
2. The receiver inspects its local `downloads/` directory. If a file with the identical name exists but its size is strictly smaller than the target size, the receiver mathematically calculates how many complete 1400-byte chunks it cleanly possesses.
3. The receiver actively truncates any incomplete, dangling byte fragments at the end of the file and responds to the sender with an `ACK` containing the exact sequence chunk number it must resume from.
4. The sender dynamically fast-forwards its local file pointer (`file.seek()`) to this byte offset and immediately begins transmitting the missing data.

## 4. Multiclient Inbound Multiplexing

The receiver logic operates as a true headless daemon. Early iterations of network projects often utilize global variables to track "the current transfer." 

In contrast, this project maintains a hash map of connections utilizing the Sender's unique `(IP address, Port)` tuple as the routing key. This completely isolates the sequence tracking, out-of-order buffers, and I/O file objects for all incoming packets. This architecture guarantees the receiver node can independently and securely construct dozens of files from completely different peers simultaneously over the single bound UDP socket.
