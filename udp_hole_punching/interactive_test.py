#!/usr/bin/env python3
"""
Interactive Test - Server and Client with Manual Typing

Run this and type messages to see them echoed back!
Press Ctrl+C to stop.
"""

import os
import sys
import time
import threading
import socket
import secrets
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from security.encryption import CryptoManager, derive_session_keys
from protocol.messages import Message, MessageType


def main():
    print("="*60)
    print("Interactive Test - Type messages to chat!")
    print("="*60)
    print()
    
    # Setup
    shared_secret = secrets.token_bytes(32)
    connection_id = f"interactive-{int(time.time())}"
    server_ip = "127.0.0.1"
    server_port = 55555
    
    print(f"Server: {server_ip}:{server_port}")
    print(f"Connection ID: {connection_id}")
    print()
    
    # Events
    server_ready = threading.Event()
    stop_event = threading.Event()
    
    # Shared socket for client (server will update this)
    client_socket = None
    server_socket = None
    crypto = None
    server_thread = None
    
    try:
        # Setup crypto
        crypto = CryptoManager()
        keys = derive_session_keys(shared_secret, connection_id, int(time.time()))
        crypto.set_session_keys(keys)
        
        # Create and bind server socket
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((server_ip, server_port))
        server_socket.settimeout(0.5)
        
        print("[1] Server started!")
        print("[2] Starting client connection...")
        
        # Create client socket and connect directly
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        client_socket.settimeout(2.0)
        
        print("[3] Connected! Type your messages below.")
        print("-" * 60)
        print("Type a message and press Enter to send.")
        print("Type 'quit' or press Ctrl+C to exit.")
        print("-" * 60)
        print()
        
        # Start server thread
        server_thread = threading.Thread(
            target=server_loop,
            args=(server_socket, crypto, stop_event)
        )
        server_thread.daemon = True
        server_thread.start()
        
        # Start receive thread for client
        receive_thread = threading.Thread(
            target=client_receive_loop,
            args=(client_socket, crypto, stop_event)
        )
        receive_thread.daemon = True
        receive_thread.start()
        
        # Main input loop
        while not stop_event.is_set():
            try:
                msg = input("> ").strip()
                
                if not msg:
                    continue
                
                if msg.lower() == 'quit':
                    break
                
                # Send message
                send_message(client_socket, crypto, msg, (server_ip, server_port))
                
            except EOFError:
                break
            except KeyboardInterrupt:
                break
    
    except Exception as e:
        print(f"Error: {e}")
    
    finally:
        print()
        print("[4] Shutting down...")
        stop_event.set()
        
        if server_thread:
            server_thread.join(timeout=1)
        
        if server_socket:
            server_socket.close()
        if client_socket:
            client_socket.close()
        
        print("Done!")


def server_loop(sock, crypto, stop_event):
    """Server receive loop."""
    client_addr = None
    
    while not stop_event.is_set():
        try:
            data, addr = sock.recvfrom(2048)
            
            # Decrypt
            try:
                plaintext = crypto.decrypt_packet(data)
                msg = Message.from_bytes(plaintext)
            except:
                continue
            
            if msg.msg_type == MessageType.CHAT:
                text = msg.payload.get('text', '')
                sender = msg.payload.get('sender', 'client')
                
                # Print to console
                print(f"\n[Server received] {text}")
                print("> ", end='', flush=True)
                
                # Store client address
                if not client_addr:
                    client_addr = addr
                    print(f"\n[Client connected from {addr}]")
                    print("> ", end='', flush=True)
                
                # Echo back
                if client_addr:
                    response = Message(
                        msg_type=MessageType.CHAT,
                        payload={'text': f"Echo: {text}", 'sender': 'server'}
                    )
                    enc = crypto.encrypt_packet(response.to_bytes())
                    sock.sendto(enc, client_addr)
                    
        except socket.timeout:
            continue
        except Exception:
            break


def client_receive_loop(sock, crypto, stop_event):
    """Client receive loop."""
    while not stop_event.is_set():
        try:
            sock.settimeout(1.0)
            data, addr = sock.recvfrom(2048)
            
            # Decrypt
            try:
                plaintext = crypto.decrypt_packet(data)
                msg = Message.from_bytes(plaintext)
            except:
                continue
            
            if msg.msg_type == MessageType.CHAT:
                text = msg.payload.get('text', '')
                sender = msg.payload.get('sender', 'server')
                
                # Print to console
                print(f"\n[{sender}] {text}")
                print("> ", end='', flush=True)
                
        except socket.timeout:
            continue
        except Exception:
            break


def send_message(sock, crypto, text, server_addr):
    """Send a chat message."""
    msg = Message(
        msg_type=MessageType.CHAT,
        payload={'text': text, 'sender': 'you'}
    )
    enc = crypto.encrypt_packet(msg.to_bytes())
    sock.sendto(enc, server_addr)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nGoodbye!")
        sys.exit(0)
