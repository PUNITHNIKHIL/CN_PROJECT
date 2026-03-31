# Architecture & Protocol Design

This document maps out the underlying mechanics of the Reliable P2P File Transfer Protocol. Because raw UDP intrinsically does not guarantee delivery, ordering, or data integrity, this custom protocol was hand-designed to build TCP-like reliability and military-grade encryption directly at the application layer.

## 1. Custom Packet Structure

Every chunk of data routed over the network is encapsulated within a custom binary header crafted utilizing Python's `struct` module. 

| Field | Size | Description |
| :--- | :---: | :--- |
| **Sequence Number** | 4 bytes | Identifies the exact chunk offset mathematically to guarantee ordering. |
| **Acknowledgment Number** | 4 bytes | Used by the receiver to declare which specific chunk was successfully locked in. |
| **Flags** | 1 byte | Bitmask indicating packet intent (`SYN` = Handshake, `ACK` = Acknowledgment, `FIN` = End of Transfer, `DATA` = File Fragment). |
| **Checksum** | 4 bytes | A CRC32 hash computed exclusively on the payload to detect network corruption. |
| **Encrypted Payload**| <= 1400 bytes| Raw file data dynamically encrypted via AES-256-CTR. |

## 2. Reliability & Throughput: Selective Repeat ARQ

To ensure no physical packets are permanently lost while dynamically maximizing network throughput, the transmitter deploys **Selective Repeat Automatic Repeat Request (ARQ)**.

1. **Sliding Window:** The sender does not wait for a single acknowledgment after every packet. Instead, it blasts up to 64 consecutive packets onto the network layer concurrently.
2. **Selective ACKs:** The moment the receiver parses a valid packet, it instantly routes an ACK citing that specific sequence number exclusively back to the sender.
3. **Targeted Retransmission:** The transmitter tracks a stopwatch for all unacknowledged packets in the window. If a packet expires, the sender deduces network loss and *selectively retransmits exclusively the missing block*, rather than naively flushing the entire buffer.

## 3. Dynamic Congestion Control (Jacobson / Karn Algorithms)

A critical failure point of naive UDP ARQ engines is using a static timeout (e.g., `0.5s`). If the network spikes to a `0.6s` ping, a static system will redundantly rebroadcast the entire file, catastrophically flooding the router.

This project natively implements **Jacobson's Algorithm**:
1. Every time a strictly fresh, non-retransmitted packet is cleanly ACKed (respecting **Karn’s Algorithm** to avoid ambiguous timing samples), the sender seamlessly tracks the precise Round Trip Time (`Sample_RTT`).
2. The sender mathematically updates an Exponentially Weighted Moving Average (EWMA) to smoothly filter the `Estimated_RTT` alongside the network variance/deviation (`Dev_RTT`).
3. The timeout timer dynamically adjusts in real-time exactly to `Estimated_RTT + (4 * Dev_RTT)`.
4. **Exponential Backoff:** If a severe congestion event forces a retransmission, the dynamic timeout is explicitly doubled (`x2.0`) to mathematically grant the network hardware breathing room to recover.

## 4. End-to-End Cryptography (ECDH Key Exchange)

The protocol utilizes an industry-standard Diffie-Hellman implementation via the Python `cryptography` library for seamless, passwordless security wrapper operations.

1. **Exchange:** During the initial `SYN` handshake step, the Sender spawns a mathematical Elliptic Curve Diffie-Hellman (`ECDH SECP384R1`) keypair, broadcasting its Public Key. The receiver calculates and responds with its own newly minted Public Key. Both machines instantaneously derive an identically shared AES Secret via `HKDF`.
2. **AES-256-CTR:** AES Counter-Mode is utilized to individually encrypt every single file block payload *pre-transmission*. Counter mode is selected because it strictly preserves byte-size with absolutely zero padding overhead—which maintains perfectly predictable UDP network chunk alignments.

## 5. The Synchronization Handshake (Resumability)

Before raw file transfer commences, the `SYN` handshake checks the disk status.

1. The receiver inspects its local `downloads/` directory. If a file with an identical name exists but its size is strictly smaller than the target, the receiver mathematically deduces how many full 1400-byte UDP chunks it cleanly possesses.
2. The receiver aggressively truncates dangling byte fragments at the end of the file and instructs the sender (via `SYN+ACK`) exactly which sequence chunk to resume transmitting from.
3. Because AES-CTR operates procedurally per block, there is zero cryptographic state conflict on dropped files; the sender dynamically fast-forwards its file pointer, logically resumes encryption generation on the requested target byte, and resumes seamlessly.
