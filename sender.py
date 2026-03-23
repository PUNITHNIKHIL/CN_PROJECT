import socket
import os
import json
import logging
import time
from protocol import create_packet, parse_packet, FLAG_SYN, FLAG_ACK, FLAG_FIN, FLAG_DATA, MAX_PAYLOAD_SIZE

logging.basicConfig(level=logging.INFO, format='%(asctime)s - Sender - %(message)s')

def send_file(filename, server_host='127.0.0.1', server_port=5000, window_size=64, timeout=0.5):
    if not os.path.exists(filename):
        logging.error(f"File {filename} not found.")
        return
        
    file_size = os.path.getsize(filename)
    base_name = os.path.basename(filename)
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setblocking(False)
    server_addr = (server_host, server_port)
    
    # Send SYN
    metadata = {'filename': base_name, 'size': file_size}
    syn_payload = json.dumps(metadata).encode('utf-8')
    syn_packet = create_packet(0, 0, FLAG_SYN, syn_payload)
    
    logging.info(f"Initiating transfer of {base_name} ({file_size} bytes)")
    
    resume_seq = 0
    handshake_done = False
    
    # Simple blocking handshake loop
    sock.settimeout(2.0)
    while not handshake_done:
        try:
            sock.sendto(syn_packet, server_addr)
            packet, addr = sock.recvfrom(65535)
            parsed = parse_packet(packet)
            if parsed:
                seq, ack, flags, payload = parsed
                if (flags & FLAG_SYN) and (flags & FLAG_ACK):
                    resume_seq = ack
                    handshake_done = True
        except socket.timeout:
            logging.warning("SYN timeout, retrying...")
            
    logging.info(f"Handshake complete. Resuming from seq: {resume_seq}")
    
    file_f = open(filename, 'rb')
    file_f.seek(resume_seq * MAX_PAYLOAD_SIZE)
    
    base_seq = resume_seq
    next_seq = resume_seq
    total_chunks = (file_size + MAX_PAYLOAD_SIZE - 1) // MAX_PAYLOAD_SIZE
    
    # Window: {seq_num: {'packet': bytes, 'time': float, 'acked': bool}}
    window = {}
    sock.settimeout(0.01) # Small timeout for receiving ACKs quickly
    
    start_time = time.time()
    
    try:
        while base_seq < total_chunks:
            # Send packets up to window size
            while next_seq < base_seq + window_size and next_seq < total_chunks:
                if next_seq not in window:
                    chunk = file_f.read(MAX_PAYLOAD_SIZE)
                    if not chunk:
                        break # Unexpected EOF
                        
                    packet = create_packet(next_seq, 0, FLAG_DATA, chunk)
                    window[next_seq] = {'packet': packet, 'time': time.time(), 'acked': False}
                    sock.sendto(packet, server_addr)
                next_seq += 1
                
            # Process incoming ACKs
            try:
                # Read all available ACKs
                while True:
                    packet, addr = sock.recvfrom(65535)
                    parsed = parse_packet(packet)
                    if parsed:
                        seq, ack, flags, payload = parsed
                        if flags & FLAG_ACK:
                            # Receiver sends seq_num in ACK packet
                            if ack in window:
                                window[ack]['acked'] = True
            except (socket.timeout, BlockingIOError):
                pass
                
            # Slide window
            while base_seq in window and window[base_seq]['acked']:
                del window[base_seq]
                base_seq += 1
                
            # Retransmit unacknowledged packets after timeout
            current_time = time.time()
            for seq_num in range(base_seq, next_seq):
                if seq_num in window and not window[seq_num]['acked']:
                    if current_time - window[seq_num]['time'] > timeout:
                        # logging.debug(f"Retransmitting seq {seq_num}")
                        sock.sendto(window[seq_num]['packet'], server_addr)
                        window[seq_num]['time'] = current_time
                        
    except KeyboardInterrupt:
        logging.info("Interrupted by user. Exiting.")
        file_f.close()
        sock.close()
        return
        
    file_f.close()
    
    elapsed = time.time() - start_time
    logging.info(f"All chunks sent and acknowledged in {elapsed:.2f} seconds.")
    
    # Send FIN
    fin_packet = create_packet(0, 0, FLAG_FIN)
    sock.settimeout(2.0)
    for _ in range(5):
        try:
            sock.sendto(fin_packet, server_addr)
            packet, addr = sock.recvfrom(65535)
            parsed = parse_packet(packet)
            if parsed:
                seq, ack, flags, payload = parsed
                if (flags & FLAG_FIN) and (flags & FLAG_ACK):
                    logging.info("FIN+ACK received. Transfer complete.")
                    break
        except socket.timeout:
            logging.warning("FIN timeout, retrying...")
            
    sock.close()

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('file', help='File to send')
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=5000)
    parser.add_argument('--window', type=int, default=64)
    parser.add_argument('--timeout', type=float, default=0.5)
    args = parser.parse_args()
    send_file(args.file, args.host, args.port, args.window, args.timeout)
