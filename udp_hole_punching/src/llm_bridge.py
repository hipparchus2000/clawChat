#!/usr/bin/env python3
"""
LLM Bridge - Persistent LLM Session for ClawChat

Maintains conversation history and provides stdin/stdout interface
for ClawChat server to interact with any LLM (DeepSeek, OpenAI, etc.)
"""

import os
import sys
import json
import time
import queue
import threading
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Callable
from datetime import datetime


@dataclass
class Message:
    """A message in the conversation."""
    role: str  # 'user', 'assistant', 'system'
    content: str
    timestamp: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()
    
    def to_dict(self) -> dict:
        return {
            'role': self.role,
            'content': self.content,
            'timestamp': self.timestamp
        }


class LLMConfig:
    """Configuration for LLM provider."""
    
    PROVIDERS = {
        'deepseek': {
            'api_base': 'https://api.deepseek.com/v1',
            'model': 'deepseek-chat',
            'api_key_env': 'DEEPSEEK_API_KEY'
        },
        'openai': {
            'api_base': 'https://api.openai.com/v1',
            'model': 'gpt-3.5-turbo',
            'api_key_env': 'OPENAI_API_KEY'
        },
        'anthropic': {
            'api_base': 'https://api.anthropic.com/v1',
            'model': 'claude-3-haiku-20240307',
            'api_key_env': 'ANTHROPIC_API_KEY'
        }
    }
    
    def __init__(self, provider: str = 'deepseek'):
        self.provider = provider.lower()
        if self.provider not in self.PROVIDERS:
            raise ValueError(f"Unknown provider: {provider}")
        
        config = self.PROVIDERS[self.provider]
        self.api_base = config['api_base']
        self.model = config['model']
        self.api_key = os.environ.get(config['api_key_env'])
        
        if not self.api_key:
            print(f"Warning: {config['api_key_env']} not set")


class LLMBridge:
    """
    Persistent LLM session bridge.
    
    Maintains conversation history and provides interface for
    external clients (like ClawChat) to interact with LLM.
    """
    
    def __init__(self, config: Optional[LLMConfig] = None, save_file: Optional[str] = None):
        """
        Initialize LLM bridge.
        
        Args:
            config: LLM configuration (default: DeepSeek)
            save_file: Path to save/load conversation history
        """
        self.config = config or LLMConfig('deepseek')
        self.save_file = save_file or 'llm_session.json'
        
        # Conversation history
        self.messages: List[Message] = []
        self.system_prompt: Optional[str] = None
        
        # Input/output queues for stdin/stdout style interface
        self.input_queue: queue.Queue[str] = queue.Queue()
        self.output_queue: queue.Queue[str] = queue.Queue()
        
        # State
        self.running = False
        self.processing = False
        self.session_thread: Optional[threading.Thread] = None
        
        # Load existing session
        self.load_session()
    
    def load_session(self):
        """Load conversation history from file."""
        if os.path.exists(self.save_file):
            try:
                with open(self.save_file, 'r') as f:
                    data = json.load(f)
                    
                self.messages = [Message(**m) for m in data.get('messages', [])]
                self.system_prompt = data.get('system_prompt')
                
                print(f"[LLM Bridge] Loaded {len(self.messages)} messages from {self.save_file}")
            except Exception as e:
                print(f"[LLM Bridge] Failed to load session: {e}")
    
    def save_session(self):
        """Save conversation history to file."""
        try:
            data = {
                'messages': [m.to_dict() for m in self.messages],
                'system_prompt': self.system_prompt,
                'last_saved': time.time()
            }
            
            with open(self.save_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            print(f"[LLM Bridge] Failed to save session: {e}")
    
    def set_system_prompt(self, prompt: str):
        """Set system prompt for the conversation."""
        self.system_prompt = prompt
        # Remove old system message if exists
        self.messages = [m for m in self.messages if m.role != 'system']
        # Add new system message
        self.messages.insert(0, Message(role='system', content=prompt))
        self.save_session()
    
    def add_message(self, role: str, content: str):
        """Add a message to history."""
        self.messages.append(Message(role=role, content=content))
        self.save_session()
    
    def get_context_window(self, max_messages: int = 20) -> List[dict]:
        """Get recent messages for API context."""
        # Always include system prompt if set
        context = []
        if self.system_prompt:
            context.append({'role': 'system', 'content': self.system_prompt})
        
        # Add recent messages
        recent = self.messages[-max_messages:] if len(self.messages) > max_messages else self.messages
        for msg in recent:
            if msg.role != 'system':  # Skip system messages (we added it above)
                context.append({'role': msg.role, 'content': msg.content})
        
        return context
    
    def send_to_llm(self, user_message: str) -> str:
        """
        Send message to LLM and get response.
        
        Args:
            user_message: User's input
            
        Returns:
            LLM response
        """
        # Add user message to history
        self.add_message('user', user_message)
        
        # Call LLM API based on provider
        if self.config.provider == 'deepseek':
            response = self._call_deepseek(user_message)
        elif self.config.provider == 'openai':
            response = self._call_openai(user_message)
        elif self.config.provider == 'anthropic':
            response = self._call_anthropic(user_message)
        else:
            response = f"[Error: Unknown provider {self.config.provider}]"
        
        # Add assistant response to history
        self.add_message('assistant', response)
        
        return response
    
    def _call_deepseek(self, user_message: str) -> str:
        """Call DeepSeek API."""
        try:
            import requests
            
            headers = {
                'Authorization': f'Bearer {self.config.api_key}',
                'Content-Type': 'application/json'
            }
            
            data = {
                'model': self.config.model,
                'messages': self.get_context_window(),
                'stream': False
            }
            
            response = requests.post(
                f'{self.config.api_base}/chat/completions',
                headers=headers,
                json=data,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content']
            else:
                return f"[Error: DeepSeek API returned {response.status_code}: {response.text}]"
                
        except Exception as e:
            return f"[Error calling DeepSeek: {e}]"
    
    def _call_openai(self, user_message: str) -> str:
        """Call OpenAI API."""
        try:
            import requests
            
            headers = {
                'Authorization': f'Bearer {self.config.api_key}',
                'Content-Type': 'application/json'
            }
            
            data = {
                'model': self.config.model,
                'messages': self.get_context_window(),
                'stream': False
            }
            
            response = requests.post(
                f'{self.config.api_base}/chat/completions',
                headers=headers,
                json=data,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content']
            else:
                return f"[Error: OpenAI API returned {response.status_code}: {response.text}]"
                
        except Exception as e:
            return f"[Error calling OpenAI: {e}]"
    
    def _call_anthropic(self, user_message: str) -> str:
        """Call Anthropic Claude API."""
        try:
            import requests
            
            headers = {
                'x-api-key': self.config.api_key,
                'Content-Type': 'application/json',
                'anthropic-version': '2023-06-01'
            }
            
            # Anthropic uses different format
            messages = []
            system = None
            for msg in self.get_context_window():
                if msg['role'] == 'system':
                    system = msg['content']
                else:
                    messages.append(msg)
            
            data = {
                'model': self.config.model,
                'messages': messages,
                'max_tokens': 1024
            }
            if system:
                data['system'] = system
            
            response = requests.post(
                f'{self.config.api_base}/messages',
                headers=headers,
                json=data,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                return result['content'][0]['text']
            else:
                return f"[Error: Anthropic API returned {response.status_code}: {response.text}]"
                
        except Exception as e:
            return f"[Error calling Anthropic: {e}]"
    
    # ============== Stdin/Stdout Interface ==============
    
    def write(self, text: str):
        """Write input to the LLM (like stdin)."""
        self.input_queue.put(text)
    
    def read(self, timeout: Optional[float] = None) -> Optional[str]:
        """Read output from LLM (like stdout)."""
        try:
            return self.output_queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def read_nowait(self) -> Optional[str]:
        """Read output without blocking."""
        try:
            return self.output_queue.get_nowait()
        except queue.Empty:
            return None
    
    # ============== Session Management ==============
    
    def start(self):
        """Start the background processing thread."""
        if self.running:
            return
        
        self.running = True
        self.session_thread = threading.Thread(target=self._process_loop, daemon=True)
        self.session_thread.start()
        print(f"[LLM Bridge] Started with {self.config.provider} provider")
    
    def stop(self):
        """Stop the background processing."""
        self.running = False
        if self.session_thread:
            self.session_thread.join(timeout=2)
        self.save_session()
        print("[LLM Bridge] Stopped")
    
    def _process_loop(self):
        """Background processing loop."""
        while self.running:
            try:
                # Wait for input
                user_input = self.input_queue.get(timeout=0.5)
                
                # Mark as processing
                self.processing = True
                
                # Get response from LLM
                response = self.send_to_llm(user_input)
                
                # Put in output queue
                self.output_queue.put(response)
                
                self.processing = False
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"[LLM Bridge] Processing error: {e}")
                self.processing = False
    
    def is_processing(self) -> bool:
        """Check if currently processing a request."""
        return self.processing
    
    def get_history(self) -> List[Message]:
        """Get full conversation history."""
        return self.messages.copy()
    
    def clear_history(self):
        """Clear conversation history."""
        self.messages = []
        if self.system_prompt:
            self.messages.append(Message(role='system', content=self.system_prompt))
        self.save_session()


# ============== Simple CLI Interface ==============

def main():
    """Run LLM bridge in CLI mode."""
    import argparse
    
    parser = argparse.ArgumentParser(description='LLM Bridge for ClawChat')
    parser.add_argument('--provider', default='deepseek', choices=['deepseek', 'openai', 'anthropic'])
    parser.add_argument('--save-file', default='llm_session.json')
    parser.add_argument('--system-prompt', default='You are a helpful assistant.')
    
    args = parser.parse_args()
    
    # Create config
    config = LLMConfig(args.provider)
    
    # Create bridge
    bridge = LLMBridge(config, args.save_file)
    bridge.set_system_prompt(args.system_prompt)
    bridge.start()
    
    print("="*60)
    print(f"LLM Bridge - {args.provider}")
    print("="*60)
    print("Type messages to chat. Type 'quit' to exit.")
    print("Type 'clear' to clear history.")
    print("Type 'history' to show conversation.")
    print("-"*60)
    
    try:
        while True:
            # Get input
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
                print("\n--- Conversation History ---")
                for msg in bridge.get_history():
                    if msg.role != 'system':
                        time_str = datetime.fromtimestamp(msg.timestamp).strftime('%H:%M:%S')
                        print(f"[{time_str}] {msg.role}: {msg.content[:100]}...")
                print("---")
                continue
            
            # Send to LLM
            bridge.write(user_input)
            print("Assistant: ", end='', flush=True)
            
            # Wait for response
            while True:
                response = bridge.read(timeout=0.1)
                if response:
                    print(response)
                    break
                if not bridge.is_processing() and bridge.input_queue.empty():
                    # No response and not processing
                    break
    
    except KeyboardInterrupt:
        print("\n\nGoodbye!")
    finally:
        bridge.stop()


if __name__ == '__main__':
    main()
