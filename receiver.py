import socket
import os
import json
import logging
from protocol import create_packet, parse_packet, FLAG_SYN, FLAG_ACK, FLAG_FIN, FLAG_DATA, MAX_PAYLOAD_SIZE

logging.basicConfig(level=logging.INFO, format='%(asctime)s - Receiver - %(message)s')

def flags_to_str(flags):
    lst = []
    if flags & FLAG_SYN: lst.append('SYN')
    if flags & FLAG_ACK: lst.append('ACK')
    if flags & FLAG_FIN: lst.append('FIN')
    if flags & FLAG_DATA: lst.append('DATA')
    return "|".join(lst)

def start_receiver(host='0.0.0.0', port=5000, download_dir='downloads'):
    os.makedirs(download_dir, exist_ok=True)
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((host, port))
    logging.info(f"Listening on {host}:{port}")
    
    # Track state per active sender client
    # clients mapping: addr -> {'expected_seq': int, 'file_f': file_obj, 'file_path': str, 'buffer': {seq: payload}}
    clients = {}
    
    while True:
        try:
            packet, addr = sock.recvfrom(65535)
            parsed = parse_packet(packet)
            
            if not parsed:
                continue # Corrupted
                
            seq_num, ack_num, flags, payload = parsed
            
            # Print/Log every packet received
            logging.info(f"Received from {addr} | Seq: {seq_num} | Ack: {ack_num} | Flags: {flags_to_str(flags)} | Length: {len(payload)} bytes")
            
            if addr not in clients:
                clients[addr] = {'expected_seq': 0, 'file_f': None, 'file_path': None, 'buffer': {}}
                
            client = clients[addr]
            
            if flags & FLAG_SYN:
                try:
                    metadata = json.loads(payload.decode('utf-8'))
                    filename = metadata['filename']
                    file_size = metadata['size']
                except json.JSONDecodeError:
                    continue
                    
                client['file_path'] = os.path.join(download_dir, filename)
                
                # Check for existing file to resume
                existing_size = 0
                if os.path.exists(client['file_path']):
                    existing_size = os.path.getsize(client['file_path'])
                    
                if existing_size > file_size:
                    existing_size = 0
                    
                client['expected_seq'] = existing_size // MAX_PAYLOAD_SIZE
                actual_resume_size = client['expected_seq'] * MAX_PAYLOAD_SIZE
                
                # Truncate to the block boundary
                if actual_resume_size > 0:
                    with open(client['file_path'], 'r+b') as f:
                        f.truncate(actual_resume_size)
                        
                if client['file_f']:
                    client['file_f'].close()
                client['file_f'] = open(client['file_path'], 'ab')
                client['buffer'].clear()
                
                logging.info(f"Handshake complete for {filename} from {addr}. Resuming at seq {client['expected_seq']}")
                
                # Respond with SYN+ACK, ack_num is the expected_seq
                ack_packet = create_packet(0, client['expected_seq'], FLAG_SYN | FLAG_ACK)
                sock.sendto(ack_packet, addr)
                continue
                
            if flags & FLAG_DATA:
                if not client['file_f']:
                    continue
                    
                if seq_num == client['expected_seq']:
                    client['file_f'].write(payload)
                    client['file_f'].flush()
                    client['expected_seq'] += 1
                    
                    while client['expected_seq'] in client['buffer']:
                        client['file_f'].write(client['buffer'].pop(client['expected_seq']))
                        client['file_f'].flush()
                        client['expected_seq'] += 1
                        
                elif seq_num > client['expected_seq']:
                    # Only buffer if it's within a reasonable window
                    if seq_num - client['expected_seq'] < 1000:
                        client['buffer'][seq_num] = payload
                    
                # Selective ACK for the received sequence number
                ack_packet = create_packet(0, seq_num, FLAG_ACK)
                sock.sendto(ack_packet, addr)
                
            if flags & FLAG_FIN:
                logging.info(f"Transfer complete from {addr}.")
                if client['file_f']:
                    client['file_f'].close()
                del clients[addr]
                
                # Send FIN+ACK
                ack_packet = create_packet(0, seq_num, FLAG_FIN | FLAG_ACK)
                sock.sendto(ack_packet, addr)
                
        except KeyboardInterrupt:
            logging.info("Shutting down Receiver.")
            for addr, client in clients.items():
                if client['file_f']:
                    client['file_f'].close()
            break
        except Exception as e:
            logging.error(f"Error processing packet: {e}")

if __name__ == '__main__':
    start_receiver()