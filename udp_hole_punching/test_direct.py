#!/usr/bin/env python3
"""
Direct test - Import and run server and client directly in threads
"""

import os
import sys
import time
import threading
import tempfile
import socket
import secrets
import base64
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

def main():
    print("="*60)
    print("Direct Test: Server + Client")
    print("="*60)
    print()
    
    # Setup
    bootstrap_key = b"test-key-32bytes-long!!!"
    server_ip = "127.0.0.1"
    server_port = 55555
    
    # Generate shared secret
    shared_secret = secrets.token_bytes(32)
    connection_id = f"test-{int(time.time())}"
    
    print(f"Server: {server_ip}:{server_port}")
    print(f"Connection ID: {connection_id}")
    print()
    
    # Start server thread
    print("[1] Starting server...")
    server_ready = threading.Event()
    server_stop = threading.Event()
    
    server_thread = threading.Thread(
        target=run_server,
        args=(server_ip, server_port, shared_secret, connection_id, bootstrap_key, server_ready, server_stop)
    )
    server_thread.start()
    
    if not server_ready.wait(timeout=5):
        print("ERROR: Server failed to start!")
        return
    
    print("    Server ready!")
    print()
    
    # Give server time
    time.sleep(0.5)
    
    # Run client
    print("[2] Starting client...")
    print()
    
    run_client(server_ip, server_port, shared_secret, connection_id, bootstrap_key)
    
    # Stop server
    print()
    print("[3] Stopping server...")
    server_stop.set()
    server_thread.join(timeout=3)
    
    print()
    print("="*60)
    print("Test complete!")
    print("="*60)


def run_server(ip, port, shared_secret, connection_id, bootstrap_key, ready_event, stop_event):
    """Run the server."""
    from src.security.encryption import CryptoManager, derive_session_keys
    from src.protocol.messages import Message, MessageType
    
    # Setup crypto
    crypto = CryptoManager()
    keys = derive_session_keys(shared_secret, connection_id, int(time.time()))
    crypto.set_session_keys(keys)
    
    # Create socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('0.0.0.0', port))
    sock.settimeout(0.5)
    
    print(f"    [Server] Listening on {ip}:{port}")
    ready_event.set()
    
    peer_address = None
    messages_received = 0
    messages_sent = 0
    
    while not stop_event.is_set():
        try:
            data, addr = sock.recvfrom(2048)
            
            # Decrypt
            try:
                plaintext = crypto.decrypt_packet(data)
            except:
                continue
            
            msg = Message.from_bytes(plaintext)
            messages_received += 1
            
            if not peer_address:
                peer_address = addr
                print(f"    [Server] Peer connected from {addr}")
            
            # Handle message
            if msg.msg_type == MessageType.CHAT:
                text = msg.payload.get('text', '')
                sender = msg.payload.get('sender', 'unknown')
                print(f"    [Server] Received from {sender}: {text}")
                
                # Echo back
                if peer_address:
                    response = Message(
                        msg_type=MessageType.CHAT,
                        payload={'text': f"Echo: {text}", 'sender': 'server'}
                    )
                    encrypted = crypto.encrypt_packet(response.to_bytes())
                    sock.sendto(encrypted, peer_address)
                    messages_sent += 1
                    print(f"    [Server] Sent echo")
                    
            elif msg.msg_type == MessageType.PUNCH:
                print(f"    [Server] Punch received")
                if peer_address:
                    ack = Message(
                        msg_type=MessageType.PUNCH_ACK,
                        payload={'status': 'ok'}
                    )
                    encrypted = crypto.encrypt_packet(ack.to_bytes())
                    sock.sendto(encrypted, peer_address)
                    
        except socket.timeout:
            continue
        except Exception as e:
            print(f"    [Server] Error: {e}")
    
    sock.close()
    print(f"    [Server] Stopped. Received: {messages_received}, Sent: {messages_sent}")


def run_client(ip, port, shared_secret, connection_id, bootstrap_key):
    """Run the client."""
    from src.security.encryption import CryptoManager, derive_session_keys
    from src.networking.udp_hole_punch import UDPHolePuncher
    from src.protocol.messages import Message, MessageType
    
    # Setup crypto
    crypto = CryptoManager()
    keys = derive_session_keys(shared_secret, connection_id, int(time.time()))
    crypto.set_session_keys(keys)
    
    # Hole punch
    print("[Client] Performing hole punch...")
    puncher = UDPHolePuncher(
        crypto_manager=crypto,
        timeout=10.0,
        retry_interval=0.2,
        on_state_change=lambda old, new: print(f"[Client] Punch state: {old.value} -> {new.value}")
    )
    
    result = puncher.punch(ip, port)
    
    if not result.success:
        print(f"[Client] Punch failed: {result.error_message}")
        return
    
    print(f"[Client] Connected! Latency: {result.latency_ms:.1f}ms")
    
    # Send messages
    print()
    print("[Client] Sending test messages...")
    print("-" * 40)
    
    test_messages = ["Hello!", "Test message", "Final test"]
    
    for msg_text in test_messages:
        msg = Message(
            msg_type=MessageType.CHAT,
            payload={'text': msg_text, 'sender': 'client'}
        )
        encrypted = crypto.encrypt_packet(msg.to_bytes())
        puncher.socket.sendto(encrypted, (ip, port))
        print(f"[Client] Sent: {msg_text}")
        
        # Wait for response
        try:
            puncher.socket.settimeout(2.0)
            data, addr = puncher.socket.recvfrom(2048)
            plaintext = crypto.decrypt_packet(data)
            response = Message.from_bytes(plaintext)
            
            if response.msg_type == MessageType.CHAT:
                text = response.payload.get('text', '')
                print(f"[Client] Received: {text}")
                
        except socket.timeout:
            print("[Client] No response (timeout)")
        except Exception as e:
            print(f"[Client] Error receiving: {e}")
        
        print()
        time.sleep(0.3)
    
    puncher.close()
    print("-" * 40)
    print("[Client] Done!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(0)
