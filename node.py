import threading
import argparse
import sys
import os
import logging
from receiver import start_receiver
from sender import send_file

def run_node():
    parser = argparse.ArgumentParser(description="Reliable P2P UDP File Transfer Node")
    parser.add_argument('--port', type=int, default=5000, help='Port to listen on for incoming files')
    args = parser.parse_args()
    
    # Start receiver in a background daemon thread
    receiver_thread = threading.Thread(
        target=start_receiver, 
        kwargs={'host': '0.0.0.0', 'port': args.port, 'download_dir': 'downloads'},
        daemon=True
    )
    receiver_thread.start()
    
    print("="*50)
    print(f"  P2P Reliable UDP File Transfer Node")
    print(f"  Listening on port {args.port}")
    print("="*50)
    print("Type 'help' to see available commands.")
    
    active_peer = None
    
    while True:
        try:
            cmd_line = input("\nnode> ").strip()
            if not cmd_line:
                continue
                
            parts = cmd_line.split()
            cmd = parts[0].lower()
            
            if cmd in ('exit', 'quit'):
                print("Exiting...")
                sys.exit(0)
                
            elif cmd == 'help':
                print("\nCommands:")
                print("  connect <ip> <port>   - Set the destination peer (e.g. 'connect 127.0.0.1 5001')")
                print("  send <filename>       - Send a file to the connected peer over UDP")
                print("  exit / quit           - Close the application\n")
                
            elif cmd == 'connect':
                if len(parts) != 3:
                    print("Usage: connect <ip> <port>")
                    continue
                ip = parts[1]
                try:
                    port = int(parts[2])
                    active_peer = (ip, port)
                    print(f"Connected to peer {ip}:{port}")
                except ValueError:
                    print("Invalid port number.")
                    
            elif cmd == 'send':
                if len(parts) < 2:
                    print("Usage: send <filename>")
                    continue
                if not active_peer:
                    print("No peer connected. Use 'connect <ip> <port>' first.")
                    continue
                    
                # Join parts in case filename has spaces
                filename = " ".join(parts[1:])
                if not os.path.exists(filename):
                    print(f"File not found: {filename}")
                    continue
                    
                print(f"Uploading '{filename}' to {active_peer[0]}:{active_peer[1]}...")
                # Run send_file (blocking)
                send_file(filename, server_host=active_peer[0], server_port=active_peer[1])
                print(f"\nTransfer task completed.")
                
            else:
                print(f"Unknown command: {cmd}")
                
        except (KeyboardInterrupt, EOFError):
            print("\nExiting...")
            sys.exit(0)

if __name__ == "__main__":
    run_node()
