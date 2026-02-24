#!/usr/bin/env python3
"""
Test the context loading system
"""

import sys
import os

sys.path.insert(0, 'src')

from context_loader import ContextLoader, create_default_context_files


def main():
    context_dir = "./context"
    
    print("="*60)
    print("Context Loader Test")
    print("="*60)
    print()
    
    # Create default files
    print("[1] Creating default context files...")
    create_default_context_files(context_dir)
    print()
    
    # Load context
    print("[2] Loading context...")
    loader = ContextLoader(context_dir)
    prompt = loader.load_all()
    print()
    
    # Show loaded files
    print("[3] Loaded files (in priority order):")
    for name in loader.get_loaded_files():
        print(f"   [OK] {name}")
    print()
    
    # Show assembled prompt
    print("[4] Assembled system prompt:")
    print("-"*60)
    print(prompt[:2000] + "..." if len(prompt) > 2000 else prompt)
    print("-"*60)
    print()
    
    print("Test complete!")
    print(f"Context directory: {os.path.abspath(context_dir)}")


if __name__ == "__main__":
    main()
