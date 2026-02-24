#!/usr/bin/env python3
"""
Run ClawChat LLM Server

Usage:
    python run_llm_server.py --provider deepseek
    python run_llm_server.py --provider openai
"""

import sys
import os
from pathlib import Path

# Load .env file if present
from dotenv import load_dotenv
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

sys.path.insert(0, 'src')

from server.llm_server import main

if __name__ == "__main__":
    main()
