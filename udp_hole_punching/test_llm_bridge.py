#!/usr/bin/env python3
"""
Test LLM Bridge - Interactive test without needing API keys
"""

import sys
import time

sys.path.insert(0, 'src')

from llm_bridge import LLMBridge, LLMConfig


def mock_llm_provider():
    """Create a mock provider that doesn't need API keys."""
    config = LLMConfig.__new__(LLMConfig)
    config.provider = 'mock'
    config.api_base = 'mock://localhost'
    config.model = 'mock-model'
    config.api_key = 'mock-key'
    return config


class MockLLMBridge(LLMBridge):
    """Mock bridge for testing without API keys."""
    
    def send_to_llm(self, user_message: str) -> str:
        """Mock response instead of calling real API."""
        self.add_message('user', user_message)
        
        # Generate mock response
        response = f"[Mock LLM] You said: '{user_message}'. This is a test response."
        
        self.add_message('assistant', response)
        return response


def main():
    print("="*60)
    print("LLM Bridge Test (Mock Mode - No API needed)")
    print("="*60)
    print()
    
    # Create mock bridge
    config = mock_llm_provider()
    bridge = MockLLMBridge(config, save_file='test_session.json')
    bridge.set_system_prompt("You are a test assistant.")
    bridge.start()
    
    print("Session started. Type messages to test.")
    print("Type 'history' to see conversation.")
    print("Type 'clear' to clear history.")
    print("Type 'quit' to exit.")
    print("-"*60)
    
    try:
        while True:
            user_input = input("\nYou: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() == 'quit':
                break
            
            if user_input.lower() == 'clear':
                bridge.clear_history()
                print("History cleared.")
                continue
            
            if user_input.lower() == 'history':
                print("\n--- History ---")
                for msg in bridge.get_history():
                    if msg.role != 'system':
                        print(f"  {msg.role}: {msg.content}")
                print("---")
                continue
            
            # Send and get response
            bridge.write(user_input)
            
            # Wait for response
            while True:
                response = bridge.read(timeout=0.1)
                if response:
                    print(f"Assistant: {response}")
                    break
                if not bridge.is_processing():
                    break
    
    except KeyboardInterrupt:
        print("\n\nStopping...")
    finally:
        bridge.stop()
        print("Session saved.")


if __name__ == '__main__':
    main()
