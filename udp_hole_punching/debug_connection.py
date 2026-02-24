#!/usr/bin/env python3
"""
Debug the connection issue
"""

import os
import sys
import json
import socket

sys.path.insert(0, 'src')

# Find the security file
sec_dir = r"C:\temp\clawchat\security"
sec_files = [f for f in os.listdir(sec_dir) if f.endswith('.sec')]

if not sec_files:
    print("No security files found!")
    sys.exit(1)

sec_path = os.path.join(sec_dir, sec_files[0])
print(f"Security file: {sec_path}")

# Load and decrypt
from security.encryption import CryptoManager
from security.file_manager import SecurityFileManager

bootstrap_key = os.environ.get('CLAWCHAT_BOOTSTRAP_KEY', 'default-key-32bytes-for-testing!').encode()[:32]
print(f"Bootstrap key: {bootstrap_key[:20]}...")

try:
    manager = SecurityFileManager(bootstrap_key=bootstrap_key)
    sec = manager.load_security_file(sec_path)
    
    print(f"\nSecurity file contents:")
    print(f"  Server IP: {sec.server_public_ip}")
    print(f"  Server Port: {sec.server_udp_port}")
    print(f"  Connection ID: {sec.connection_id}")
    
except Exception as e:
    print(f"Failed to load: {e}")
    sys.exit(1)

# Test if we can create a socket and connect
print(f"\nTesting socket connection to {sec.server_public_ip}:{sec.server_udp_port}...")

try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(2.0)
    
    # Try sending a test packet
    test_data = b"test"
    sock.sendto(test_data, (sec.server_public_ip, sec.server_udp_port))
    print("  Send succeeded!")
    
    try:
        data, addr = sock.recvfrom(1024)
        print(f"  Received response from {addr}")
    except socket.timeout:
        print("  No response (server may not be running)")
    
    sock.close()
    
except Exception as e:
    print(f"  Socket error: {e}")

# Check what addresses are available
print(f"\nLocal addresses:")
hostname = socket.gethostname()
print(f"  Hostname: {hostname}")
try:
    local_ip = socket.gethostbyname(hostname)
    print(f"  Local IP: {local_ip}")
except:
    print(f"  Could not get local IP")

print(f"\nRecommendation:")
if sec.server_public_ip not in ['127.0.0.1', 'localhost', '0.0.0.0']:
    print(f"  Server IP is '{sec.server_public_ip}' - should be '127.0.0.1' for local testing")
else:
    print(f"  Server IP looks correct: {sec.server_public_ip}")
