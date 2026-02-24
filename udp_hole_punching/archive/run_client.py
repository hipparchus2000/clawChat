#!/usr/bin/env python3
"""
ClawChat UDP Client - Entry Point

Usage:
    python run_client.py
    python run_client.py --file /path/to/security.sec
    
Environment Variables:
    CLAWCHAT_BOOTSTRAP_KEY - Key for decrypting security files
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.client.main import main

if __name__ == "__main__":
    main()
