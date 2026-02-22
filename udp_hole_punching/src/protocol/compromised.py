"""
Compromised Protocol for ClawChat.

Emergency key rotation protocol that:
1. Signals compromise through encrypted channel
2. Destroys all keys on both sides
3. Generates new security file (server)
4. Requires manual file transfer to reconnect
"""

import json
import time
import hashlib
import secrets
from enum import Enum, auto
from typing import Optional, Callable
from dataclasses import dataclass


class CompromisedState(Enum):
    """State of compromised protocol."""
    NORMAL = auto()
    SIGNAL_SENT = auto()
    SIGNAL_RECEIVED = auto()
    KEYS_DESTROYED = auto()
    WAITING_FOR_NEW_KEYS = auto()


@dataclass
class CompromisedSignal:
    """Compromised signal message."""
    signal: str
    timestamp: int
    connection_id: str
    reason: str
    signature: str


class CompromisedProtocolHandler:
    """
    Handles the Compromised Protocol for emergency key rotation.
    
    Protocol flow:
    1. Client sends COMPROMISED signal through encrypted channel
    2. Server acknowledges and both sides delete keys
    3. Server generates new security file
    4. User manually transfers new file to client
    5. Client loads new file and reconnects
    """
    
    SIGNAL_STRING = "CLAWCHAT_COMPROMISED_V2"
    ACK_STRING = "CLAWCHAT_COMPROMISED_ACK_V2"
    
    def __init__(
        self,
        is_server: bool,
        connection_id: str,
        mac_key: bytes,
        on_keys_destroyed: Optional[Callable] = None,
        on_new_file_generated: Optional[Callable] = None
    ):
        """
        Initialize handler.
        
        Args:
            is_server: True if running on server
            connection_id: Current connection ID
            mac_key: Key for HMAC signatures
            on_keys_destroyed: Callback when keys are destroyed
            on_new_file_generated: Callback when new file generated (server only)
        """
        self.is_server = is_server
        self.connection_id = connection_id
        self.mac_key = mac_key
        self.on_keys_destroyed = on_keys_destroyed
        self.on_new_file_generated = on_new_file_generated
        
        self.state = CompromisedState.NORMAL
        self.signal_sent_time: Optional[float] = None
    
    def _sign_signal(self, signal_data: str) -> str:
        """Create HMAC signature for signal."""
        h = hashlib.blake2b(key=self.mac_key, digest_size=32)
        h.update(signal_data.encode())
        return h.hexdigest()
    
    def _verify_signal(self, signal_data: str, signature: str) -> bool:
        """Verify HMAC signature."""
        expected = self._sign_signal(signal_data)
        return secrets.compare_digest(expected, signature)
    
    def create_compromised_signal(self, reason: str = "user_initiated") -> dict:
        """
        Create a compromised signal message.
        
        Args:
            reason: Reason for compromise (user_initiated, suspected_breach, etc.)
            
        Returns:
            Signal message dictionary
        """
        timestamp = int(time.time())
        
        # Create signal data
        signal_data = f"{self.SIGNAL_STRING}:{self.connection_id}:{timestamp}"
        signature = self._sign_signal(signal_data)
        
        signal = {
            'type': 'compromised',
            'version': '2.0',
            'signal': self.SIGNAL_STRING,
            'timestamp': timestamp,
            'connection_id': self.connection_id,
            'reason': reason,
            'signature': signature
        }
        
        self.state = CompromisedState.SIGNAL_SENT
        self.signal_sent_time = time.time()
        
        return signal
    
    def create_ack_signal(self, new_file_ready: bool = False) -> dict:
        """
        Create acknowledgment signal (server only).
        
        Args:
            new_file_ready: Whether new security file is ready
            
        Returns:
            ACK message dictionary
        """
        timestamp = int(time.time())
        
        signal_data = f"{self.ACK_STRING}:{self.connection_id}:{timestamp}"
        signature = self._sign_signal(signal_data)
        
        return {
            'type': 'compromised_ack',
            'version': '2.0',
            'signal': self.ACK_STRING,
            'timestamp': timestamp,
            'connection_id': self.connection_id,
            'action': 'keys_deleted',
            'new_file_ready': new_file_ready,
            'signature': signature
        }
    
    def handle_compromised_signal(self, message: dict) -> bool:
        """
        Handle received compromised signal.
        
        Args:
            message: Received signal message
            
        Returns:
            True if signal is valid and accepted
        """
        try:
            # Validate message type
            if message.get('type') != 'compromised':
                return False
            
            if message.get('version') != '2.0':
                return False
            
            if message.get('signal') != self.SIGNAL_STRING:
                return False
            
            if message.get('connection_id') != self.connection_id:
                print(f"[Compromised] Connection ID mismatch: {message.get('connection_id')} vs {self.connection_id}")
                return False
            
            # Verify signature
            signal_data = f"{self.SIGNAL_STRING}:{self.connection_id}:{message['timestamp']}"
            if not self._verify_signal(signal_data, message['signature']):
                print("[Compromised] Signature verification failed")
                return False
            
            # Check timestamp (prevent replay attacks - 5 minute window)
            now = int(time.time())
            if abs(now - message['timestamp']) > 300:
                print("[Compromised] Signal timestamp too old")
                return False
            
            print(f"[Compromised] Valid signal received: {message.get('reason')}")
            self.state = CompromisedState.SIGNAL_RECEIVED
            
            # Execute key destruction
            self._destroy_keys()
            
            return True
            
        except Exception as e:
            print(f"[Compromised] Error handling signal: {e}")
            return False
    
    def handle_ack_signal(self, message: dict) -> bool:
        """
        Handle acknowledgment signal (client only).
        
        Args:
            message: Received ACK message
            
        Returns:
            True if ACK is valid
        """
        try:
            if message.get('type') != 'compromised_ack':
                return False
            
            if message.get('version') != '2.0':
                return False
            
            if message.get('signal') != self.ACK_STRING:
                return False
            
            if message.get('connection_id') != self.connection_id:
                return False
            
            # Verify signature
            signal_data = f"{self.ACK_STRING}:{self.connection_id}:{message['timestamp']}"
            if not self._verify_signal(signal_data, message['signature']):
                return False
            
            print("[Compromised] ACK received from server")
            
            # Execute key destruction
            self._destroy_keys()
            
            return True
            
        except Exception as e:
            print(f"[Compromised] Error handling ACK: {e}")
            return False
    
    def _destroy_keys(self):
        """Destroy all cryptographic keys."""
        print("[Compromised] Destroying all keys...")
        
        # Clear MAC key
        self.mac_key = secrets.token_bytes(32)  # Replace with random
        
        self.state = CompromisedState.KEYS_DESTROYED
        
        if self.on_keys_destroyed:
            self.on_keys_destroyed()
        
        print("[Compromised] Keys destroyed. Connection terminated.")
        
        # If server, generate new security file
        if self.is_server:
            self.state = CompromisedState.WAITING_FOR_NEW_KEYS
            if self.on_new_file_generated:
                self.on_new_file_generated()
    
    def is_compromised(self) -> bool:
        """Check if connection has been compromised."""
        return self.state in (
            CompromisedState.SIGNAL_SENT,
            CompromisedState.SIGNAL_RECEIVED,
            CompromisedState.KEYS_DESTROYED,
            CompromisedState.WAITING_FOR_NEW_KEYS
        )
    
    def get_state(self) -> CompromisedState:
        """Get current state."""
        return self.state


# Example usage
if __name__ == "__main__":
    import secrets
    
    print("Compromised Protocol Example")
    print("=" * 50)
    
    # Simulate client and server
    mac_key = secrets.token_bytes(32)
    connection_id = "test-conn-123"
    
    def on_client_keys_destroyed():
        print("Client: Keys destroyed!")
    
    def on_server_keys_destroyed():
        print("Server: Keys destroyed!")
    
    def on_new_file():
        print("Server: New security file generated!")
    
    # Create handlers
    client_handler = CompromisedProtocolHandler(
        is_server=False,
        connection_id=connection_id,
        mac_key=mac_key,
        on_keys_destroyed=on_client_keys_destroyed
    )
    
    server_handler = CompromisedProtocolHandler(
        is_server=True,
        connection_id=connection_id,
        mac_key=mac_key,
        on_keys_destroyed=on_server_keys_destroyed,
        on_new_file_generated=on_new_file
    )
    
    # Client sends compromised signal
    print("\n1. Client detects compromise...")
    signal = client_handler.create_compromised_signal(reason="suspected_breach")
    print(f"Signal created: {signal['reason']}")
    
    # Server receives signal
    print("\n2. Server receives signal...")
    result = server_handler.handle_compromised_signal(signal)
    print(f"Signal accepted: {result}")
    
    # Server sends ACK
    print("\n3. Server sends ACK...")
    ack = server_handler.create_ack_signal(new_file_ready=True)
    
    # Client receives ACK
    print("\n4. Client receives ACK...")
    client_handler.handle_ack_signal(ack)
    
    print("\n5. Both sides have destroyed keys")
    print(f"Client state: {client_handler.get_state().name}")
    print(f"Server state: {server_handler.get_state().name}")
