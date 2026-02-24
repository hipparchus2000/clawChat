#!/usr/bin/env python3
"""
Quick server for testing - creates security file and listens
"""

import os
import sys
import time
import socket
import secrets

sys.path.insert(0, 'src')

from security.encryption import CryptoManager, derive_session_keys
from security.file_manager import SecurityFileManager
from protocol.messages import Message, MessageType

os.makedirs(r'C:\temp\clawchat\security', exist_ok=True)

bootstrap_key = b'default-key-32bytes-for-testing!'
shared_secret = secrets.token_bytes(32)
connection_id = f'server-{int(time.time())}'

# Create security file
file_manager = SecurityFileManager(r'C:\temp\clawchat\security', bootstrap_key)
sec_path = file_manager.create_security_file(
    server_id='test-server',
    server_name='Test Server',
    server_ip='127.0.0.1',
    server_port=55555,
    shared_secret=shared_secret,
    validity_minutes=11,  # Valid for 11 minutes
    connection_id=connection_id
)
print(f'Security file created: {sec_path} (valid for 11 minutes)')

# Setup crypto
crypto = CryptoManager()
keys = derive_session_keys(shared_secret, connection_id, int(time.time()))
crypto.set_session_keys(keys)

# Create socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.bind(('0.0.0.0', 55555))
sock.settimeout(1.0)

print('Server listening on 127.0.0.1:55555')
print('Press Ctrl+C to stop')

client_addr = None
while True:
    try:
        data, addr = sock.recvfrom(2048)
        try:
            plaintext = crypto.decrypt_packet(data)
            msg = Message.from_bytes(plaintext)
            if msg.msg_type == MessageType.CHAT:
                text = msg.payload.get('text', '')
                print(f'Received: {text}')
                if not client_addr:
                    client_addr = addr
                # Echo back
                response = Message(msg_type=MessageType.CHAT, payload={'text': f'Echo: {text}', 'sender': 'server'})
                sock.sendto(crypto.encrypt_packet(response.to_bytes()), client_addr)
                print(f'Sent: Echo: {text}')
        except Exception as e:
            print(f'Decrypt error: {e}')
    except socket.timeout:
        continue
    except KeyboardInterrupt:
        break

sock.close()
print('Server stopped')
