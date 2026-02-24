#!/usr/bin/env python3
"""
Run server in background mode for testing
"""

import os
import sys
import time
import threading
from pathlib import Path

sys.path.insert(0, 'src')

os.environ['CLAWCHAT_BOOTSTRAP_KEY'] = 'default-key-32bytes-for-testing!'

from server.main import ClawChatServer

def main():
    # Create directories
    os.makedirs(r'C:\temp\clawchat\security', exist_ok=True)
    os.makedirs(r'C:\temp\clawchat\logs', exist_ok=True)
    
    # Clean old files
    for f in os.listdir(r'C:\temp\clawchat\security'):
        if f.endswith('.sec'):
            os.remove(os.path.join(r'C:\temp\clawchat\security', f))
    
    bootstrap_key = os.environ['CLAWCHAT_BOOTSTRAP_KEY'].encode()[:32]
    
    print("="*60)
    print("Starting ClawChat Server")
    print("="*60)
    print()
    print(f"IP: 127.0.0.1")
    print(f"Port: 55555")
    print(f"Security dir: C:\\temp\\clawchat\\security")
    print()
    
    server = ClawChatServer(
        security_directory=r'C:\temp\clawchat\security',
        bootstrap_key=bootstrap_key,
        server_ip='127.0.0.1',
        server_port=55555
    )
    
    try:
        server.start()
    except KeyboardInterrupt:
        print("\n\nShutting down...")
        server.stop()

if __name__ == '__main__':
    main()
