#!/usr/bin/env python3
"""
Simple Local Test - Direct connection without hole punching
"""

import os
import sys
import time
import threading
import socket
import secrets
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

def main():
    print("="*60)
    print("Simple Local Test: Direct UDP Connection")
    print("="*60)
    print()
    
    # Setup
    shared_secret = secrets.token_bytes(32)
    connection_id = f"test-{int(time.time())}"
    server_ip = "127.0.0.1"
    server_port = 55555
    
    print(f"Server: {server_ip}:{server_port}")
    print(f"Connection ID: {connection_id}")
    print()
    
    # Events
    server_ready = threading.Event()
    stop_event = threading.Event()
    
    # Start server
    print("[1] Starting server...")
    server_thread = threading.Thread(
        target=server_main,
        args=(server_ip, server_port, shared_secret, connection_id, server_ready, stop_event)
    )
    server_thread.start()
    
    if not server_ready.wait(timeout=5):
        print("ERROR: Server failed to start!")
        return
    
    time.sleep(0.5)
    
    # Run client
    print("[2] Starting client...")
    print()
    
    client_main(server_ip, server_port, shared_secret, connection_id)
    
    # Stop server
    print()
    print("[3] Stopping...")
    stop_event.set()
    server_thread.join(timeout=2)
    
    print()
    print("="*60)
    print("Test complete!")
    print("="*60)


def server_main(ip, port, shared_secret, connection_id, ready_event, stop_event):
    """Simple UDP echo server."""
    from src.security.encryption import CryptoManager, derive_session_keys
    from src.protocol.messages import Message, MessageType
    
    # Setup crypto
    crypto = CryptoManager()
    keys = derive_session_keys(shared_secret, connection_id, int(time.time()))
    crypto.set_session_keys(keys)
    
    # Create socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((ip, port))
    sock.settimeout(0.5)
    
    print(f"    [Server] Listening on {ip}:{port}")
    ready_event.set()
    
    client_addr = None
    received = 0
    sent = 0
    
    while not stop_event.is_set():
        try:
            data, addr = sock.recvfrom(2048)
            
            # Decrypt
            try:
                plaintext = crypto.decrypt_packet(data)
            except:
                continue
            
            msg = Message.from_bytes(plaintext)
            received += 1
            
            if not client_addr:
                client_addr = addr
                print(f"    [Server] Client connected: {addr}")
            
            if msg.msg_type == MessageType.CHAT:
                text = msg.payload.get('text', '')
                sender = msg.payload.get('sender', '?')
                print(f"    [Server] From {sender}: {text}")
                
                # Echo
                response = Message(
                    msg_type=MessageType.CHAT,
                    payload={'text': f"Echo: {text}", 'sender': 'server'}
                )
                enc = crypto.encrypt_packet(response.to_bytes())
                sock.sendto(enc, client_addr)
                sent += 1
                print(f"    [Server] -> Echo sent")
                
        except socket.timeout:
            continue
    
    sock.close()
    print(f"    [Server] Done. Rx: {received}, Tx: {sent}")


def client_main(ip, port, shared_secret, connection_id):
    """Simple UDP client."""
    from src.security.encryption import CryptoManager, derive_session_keys
    from src.protocol.messages import Message, MessageType
    
    # Setup crypto
    crypto = CryptoManager()
    keys = derive_session_keys(shared_secret, connection_id, int(time.time()))
    crypto.set_session_keys(keys)
    
    # Create socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(3.0)
    
    print("[Client] Connected (direct UDP)")
    print()
    
    messages = [
        "Hello Server!",
        "This is a test",
        "Working great!"
    ]
    
    sent = 0
    received = 0
    
    for text in messages:
        # Send
        msg = Message(
            msg_type=MessageType.CHAT,
            payload={'text': text, 'sender': 'client'}
        )
        enc = crypto.encrypt_packet(msg.to_bytes())
        sock.sendto(enc, (ip, port))
        sent += 1
        print(f"[Client] -> {text}")
        
        # Receive echo
        try:
            data, addr = sock.recvfrom(2048)
            plaintext = crypto.decrypt_packet(data)
            resp = Message.from_bytes(plaintext)
            
            if resp.msg_type == MessageType.CHAT:
                print(f"[Client] <- {resp.payload.get('text')}")
                received += 1
        except socket.timeout:
            print("[Client] <- (timeout, no response)")
        
        time.sleep(0.5)
        print()
    
    sock.close()
    print(f"[Client] Done. Sent: {sent}, Received: {received}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nStopped by user")
