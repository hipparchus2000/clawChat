#!/usr/bin/env python3
"""
ClawChat UDP Server - Entry Point

Usage:
    python run_server.py --ip 0.0.0.0 --port 54321
    
Environment Variables:
    CLAWCHAT_BOOTSTRAP_KEY - Key for encrypting security files
    CLAWCHAT_SECURITY_DIR - Directory for security files
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.server.main import main

if __name__ == "__main__":
    main()
