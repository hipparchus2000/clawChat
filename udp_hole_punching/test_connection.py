#!/usr/bin/env python3
"""
Test connection with matching keys
"""

import os
import sys
import time
import threading
import socket
import secrets
import base64
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from security.encryption import CryptoManager, derive_session_keys
from security.file_manager import SecurityFileManager, SecurityFile
from protocol.messages import Message, MessageType

# Use a consistent key
BOOTSTRAP_KEY = b"shared-test-key-32bytes-long!!"
SERVER_IP = "127.0.0.1"
SERVER_PORT = 55555


def main():
    print("="*60)
    print("Testing Connection with Matching Keys")
    print("="*60)
    print()
    
    # Generate shared secret
    shared_secret = secrets.token_bytes(32)
    connection_id = f"test-{int(time.time())}"
    
    print(f"Bootstrap key: {BOOTSTRAP_KEY[:20]}...")
    print(f"Server: {SERVER_IP}:{SERVER_PORT}")
    print()
    
    # Create temp directory for security file
    import tempfile
    temp_dir = tempfile.mkdtemp()
    security_dir = os.path.join(temp_dir, "security")
    os.makedirs(security_dir)
    
    # Create security file
    print("[1] Creating security file...")
    file_manager = SecurityFileManager(security_dir, BOOTSTRAP_KEY)
    
    sec_file = SecurityFile(
        version="2.0",
        protocol="clawchat-file-v2",
        server_id="test-server",
        server_name="Test Server",
        server_public_ip=SERVER_IP,
        server_udp_port=SERVER_PORT,
        shared_secret=base64.b64encode(shared_secret).decode('ascii'),
        bootstrap_key_id="bootstrap-001",
        timestamp=int(time.time()),
        valid_from=int(time.time()),
        valid_until=int(time.time()) + 3600,
        next_rotation=int(time.time()) + 3600,
        grace_period=300,
        supported_ciphers=["AES-256-GCM"],
        nat_traversal={"stun_servers": [], "hole_punch_timeout": 60},
        compromised_protocol={"signal": "CLAWCHAT_COMPROMISED_V2", "response_timeout": 10},
        connection_id=connection_id
    )
    
    crypto = CryptoManager()
    plaintext = sec_file.to_json().encode('utf-8')
    encrypted = crypto.encrypt_file(plaintext, BOOTSTRAP_KEY)
    
    import datetime
    timestamp_str = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    sec_filepath = os.path.join(security_dir, f"clawchat-{timestamp_str}.sec")
    
    import json
    with open(sec_filepath, 'w') as f:
        json.dump(encrypted, f, indent=2)
    
    print(f"    Created: {sec_filepath}")
    print()
    
    # Now try to load it back
    print("[2] Testing load security file...")
    try:
        client_manager = SecurityFileManager(bootstrap_key=BOOTSTRAP_KEY)
        loaded_sec = client_manager.load_security_file(sec_filepath)
        print(f"    Loaded successfully!")
        print(f"    Server: {loaded_sec.server_public_ip}:{loaded_sec.server_udp_port}")
        print(f"    Connection ID: {loaded_sec.connection_id}")
    except Exception as e:
        print(f"    FAILED: {e}")
        return
    
    print()
    print("[3] Starting server and client...")
    
    # Events
    server_ready = threading.Event()
    stop_event = threading.Event()
    
    # Start server
    server_thread = threading.Thread(
        target=server_main,
        args=(shared_secret, connection_id, server_ready, stop_event)
    )
    server_thread.start()
    
    if not server_ready.wait(timeout=5):
        print("ERROR: Server failed to start")
        return
    
    time.sleep(0.5)
    
    # Run client
    client_main(shared_secret, connection_id)
    
    # Cleanup
    stop_event.set()
    server_thread.join(timeout=2)
    
    # Clean up temp files
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)
    
    print()
    print("="*60)
    print("Test complete!")
    print("="*60)


def server_main(shared_secret, connection_id, ready_event, stop_event):
    """Server."""
    crypto = CryptoManager()
    keys = derive_session_keys(shared_secret, connection_id, int(time.time()))
    crypto.set_session_keys(keys)
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((SERVER_IP, SERVER_PORT))
    sock.settimeout(0.5)
    
    print(f"    [Server] Listening on {SERVER_IP}:{SERVER_PORT}")
    ready_event.set()
    
    client_addr = None
    
    while not stop_event.is_set():
        try:
            data, addr = sock.recvfrom(2048)
            
            try:
                plaintext = crypto.decrypt_packet(data)
                msg = Message.from_bytes(plaintext)
            except Exception as e:
                print(f"    [Server] Decrypt error: {e}")
                continue
            
            if msg.msg_type == MessageType.CHAT:
                text = msg.payload.get('text', '')
                sender = msg.payload.get('sender', 'client')
                print(f"    [Server] From {sender}: {text}")
                
                if not client_addr:
                    client_addr = addr
                    print(f"    [Server] Client at {addr}")
                
                # Echo
                if client_addr:
                    response = Message(
                        msg_type=MessageType.CHAT,
                        payload={'text': f"Echo: {text}", 'sender': 'server'}
                    )
                    enc = crypto.encrypt_packet(response.to_bytes())
                    sock.sendto(enc, client_addr)
                    print(f"    [Server] -> Echo sent")
                    
        except socket.timeout:
            continue
    
    sock.close()
    print(f"    [Server] Stopped")


def client_main(shared_secret, connection_id):
    """Client."""
    crypto = CryptoManager()
    keys = derive_session_keys(shared_secret, connection_id, int(time.time()))
    crypto.set_session_keys(keys)
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(3.0)
    
    print("[Client] Connected!")
    print()
    
    messages = ["Hello!", "Testing 1-2-3", "It works!"]
    
    for text in messages:
        msg = Message(
            msg_type=MessageType.CHAT,
            payload={'text': text, 'sender': 'client'}
        )
        enc = crypto.encrypt_packet(msg.to_bytes())
        sock.sendto(enc, (SERVER_IP, SERVER_PORT))
        print(f"[Client] -> {text}")
        
        try:
            data, addr = sock.recvfrom(2048)
            plaintext = crypto.decrypt_packet(data)
            resp = Message.from_bytes(plaintext)
            
            if resp.msg_type == MessageType.CHAT:
                print(f"[Client] <- {resp.payload.get('text')}")
        except socket.timeout:
            print("[Client] <- (timeout)")
        except Exception as e:
            print(f"[Client] Error: {e}")
        
        time.sleep(0.3)
        print()
    
    sock.close()
    print("[Client] Done!")


if __name__ == "__main__":
    main()
