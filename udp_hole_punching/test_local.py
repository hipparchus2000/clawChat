#!/usr/bin/env python3
"""
Local Test Script - Run both client and server on same PC

This bypasses the file browser for testing by auto-generating
the security file and having the client load it automatically.
"""

import os
import sys
import time
import threading
import subprocess
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.security.file_manager import SecurityFileManager
from src.security.encryption import derive_session_keys
import secrets
import base64


def test_local():
    """Run local test with auto-generated security file."""
    
    print("="*60)
    print("ClawChat Local Test - Client & Server on Same PC")
    print("="*60)
    print()
    
    # Setup
    bootstrap_key = b"local-test-key-32bytes-long!!!"
    server_ip = "127.0.0.1"
    server_port = 55555
    
    # Create temp directory for security file
    import tempfile
    temp_dir = tempfile.mkdtemp(prefix="clawchat_test_")
    security_dir = os.path.join(temp_dir, "security")
    os.makedirs(security_dir)
    
    print(f"Temp directory: {temp_dir}")
    print(f"Server will listen on: {server_ip}:{server_port}")
    print()
    
    # Generate security file
    print("[1] Generating security file...")
    shared_secret = secrets.token_bytes(32)
    
    file_manager = SecurityFileManager(security_dir, bootstrap_key)
    file_manager._ensure_directory()
    
    # Manually create security file
    import json
    from src.security.file_manager import SecurityFile
    
    # Generate connection ID
    connection_id = f"local-test-{int(time.time())}"
    
    security_data = SecurityFile(
        version="2.0",
        protocol="clawchat-file-v2",
        server_id="local-test-server",
        server_name="Local Test Server",
        server_public_ip=server_ip,
        server_udp_port=server_port,
        shared_secret=base64.b64encode(shared_secret).decode('ascii'),
        bootstrap_key_id="bootstrap-001",
        timestamp=int(time.time()),
        valid_from=int(time.time()),
        valid_until=int(time.time()) + 3600,
        next_rotation=int(time.time()) + 3600,
        grace_period=300,
        supported_ciphers=["AES-256-GCM"],
        nat_traversal={
            "stun_servers": ["stun.l.google.com:19302"],
            "hole_punch_timeout": 60
        },
        compromised_protocol={
            "signal": "CLAWCHAT_COMPROMISED_V2",
            "response_timeout": 10
        },
        connection_id=connection_id
    )
    
    # Encrypt and save
    from src.security.encryption import CryptoManager
    crypto = CryptoManager()
    plaintext = security_data.to_json().encode('utf-8')
    encrypted = crypto.encrypt_file(plaintext, bootstrap_key)
    
    import datetime
    timestamp_str = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    sec_filename = f"clawchat-{timestamp_str}.sec"
    sec_filepath = os.path.join(security_dir, sec_filename)
    
    with open(sec_filepath, 'w') as f:
        json.dump(encrypted, f, indent=2)
    
    print(f"    Security file created: {sec_filepath}")
    print()
    
    # Start server in background thread
    print("[2] Starting server...")
    
    server_ready = threading.Event()
    server_thread = threading.Thread(
        target=run_server,
        args=(server_ip, server_port, security_dir, bootstrap_key, shared_secret, server_ready)
    )
    server_thread.daemon = True
    server_thread.start()
    
    # Wait for server to be ready
    if not server_ready.wait(timeout=5):
        print("ERROR: Server failed to start!")
        return
    
    print("    Server started!")
    print()
    
    # Give server a moment
    time.sleep(0.5)
    
    # Start client
    print("[3] Starting client...")
    print()
    
    run_client(sec_filepath, bootstrap_key)
    
    print()
    print("="*60)
    print("Test complete!")
    print("="*60)
    
    # Cleanup
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)


def run_server(ip, port, security_dir, bootstrap_key, shared_secret, ready_event):
    """Run the server."""
    sys.path.insert(0, str(Path(__file__).parent / 'src'))
    from src.server.main import ClawChatServer
    
    server = ClawChatServer(
        security_directory=security_dir,
        bootstrap_key=bootstrap_key,
        server_ip=ip,
        server_port=port
    )
    
    # Pre-set the shared secret so it doesn't generate a new file
    server.shared_secret = shared_secret
    
    # Monkey-patch start to signal when ready
    original_start = server.start
    
    def patched_start():
        # Setup
        server.connection_id = f"{server.server_id}-{int(time.time())}"
        from src.security.encryption import CryptoManager
        server.crypto = CryptoManager()
        keys = derive_session_keys(
            server.shared_secret,
            server.connection_id,
            int(time.time())
        )
        server.crypto.set_session_keys(keys)
        
        from src.security.key_rotation import KeyRotator
        server.key_rotator = KeyRotator(
            server.shared_secret,
            server.connection_id,
            on_rotation=server._on_key_rotation
        )
        
        from src.protocol.compromised import CompromisedProtocolHandler
        server.compromised_handler = CompromisedProtocolHandler(
            is_server=True,
            connection_id=server.connection_id,
            mac_key=keys['mac_key'],
            on_keys_destroyed=server._on_keys_destroyed,
            on_new_file_generated=server._on_new_file_generated
        )
        
        import socket
        server.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        server.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.socket.bind(('0.0.0.0', server.server_port))
        server.socket.settimeout(1.0)
        
        server.running = True
        server.start_time = time.time()
        
        print(f"    [Server] Listening on {ip}:{port}")
        ready_event.set()
        
        # Main loop (simplified)
        while server.running:
            try:
                server._process_loop()
            except KeyboardInterrupt:
                break
        
        server.stop()
    
    server.start = patched_start
    
    try:
        server.start()
    except Exception as e:
        print(f"Server error: {e}")


def run_client(sec_filepath, bootstrap_key):
    """Run the client."""
    sys.path.insert(0, str(Path(__file__).parent / 'src'))
    from src.client.main import ClawChatClient
    from src.client.file_browser import SimpleFilePrompt
    
    # Monkey-patch the file browser to use our file
    original_prompt = SimpleFilePrompt.prompt
    SimpleFilePrompt.prompt = lambda title: sec_filepath
    
    client = ClawChatClient(bootstrap_key=bootstrap_key)
    
    # Load security file
    if not client.load_security_file(sec_filepath):
        print("Failed to load security file")
        return
    
    # Connect (hole punching to localhost should be instant)
    print("[Client] Connecting to server...")
    if not client.connect():
        print("Failed to connect")
        return
    
    print("[Client] Connected!")
    print()
    
    # Send test messages
    print("Sending test messages...")
    print("-" * 40)
    
    test_messages = [
        "Hello server!",
        "Testing local connection",
        "/compromised"  # This will trigger the compromised protocol
    ]
    
    for msg in test_messages:
        if msg == "/compromised":
            print()
            print("Testing Compromised Protocol...")
            client._trigger_compromised()
            time.sleep(1)
            break
        else:
            client._send_chat(msg)
            time.sleep(0.5)
    
    time.sleep(1)
    
    # Show stats
    print()
    print("-" * 40)
    print(f"Messages sent: {client.messages_sent}")
    print(f"Messages received: {client.messages_received}")
    
    client.stop()


if __name__ == "__main__":
    try:
        test_local()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(0)
