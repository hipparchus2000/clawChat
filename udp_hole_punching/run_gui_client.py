#!/usr/bin/env python3
"""
ClawChat GUI Client - Entry Point
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Now imports will work
from gui_client import main

if __name__ == "__main__":
    main()
