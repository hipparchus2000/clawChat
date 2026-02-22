"""
Key rotation module for ClawChat.

Handles in-band key rotation through the encrypted UDP channel.
"""

import time
import secrets
import hashlib
from typing import Optional, Callable
from dataclasses import dataclass

from .encryption import derive_session_keys, hkdf_extract, hkdf_expand


@dataclass
class RotationState:
    """Tracks key rotation state."""
    current_keys: dict
    next_keys: Optional[dict] = None
    rotation_due: float = 0.0
    grace_period_end: float = 0.0
    rotation_in_progress: bool = False


class KeyRotator:
    """
    Manages in-band key rotation.
    
    Keys are rotated every hour or when Compromised Protocol is triggered.
    """
    
    ROTATION_INTERVAL = 3600  # 1 hour
    GRACE_PERIOD = 300  # 5 minutes
    ADVANCE_NOTICE = 120  # 2 minutes before rotation
    
    def __init__(
        self,
        shared_secret: bytes,
        connection_id: str,
        on_rotation: Optional[Callable] = None
    ):
        """
        Initialize key rotator.
        
        Args:
            shared_secret: Initial shared secret
            connection_id: Connection identifier
            on_rotation: Callback when rotation occurs
        """
        self.shared_secret = shared_secret
        self.connection_id = connection_id
        self.on_rotation = on_rotation
        
        # Derive initial keys
        timestamp = int(time.time())
        current_keys = derive_session_keys(shared_secret, connection_id, timestamp)
        
        self.state = RotationState(
            current_keys=current_keys,
            rotation_due=time.time() + self.ROTATION_INTERVAL,
            grace_period_end=0.0
        )
        
        self._key_history = []
    
    def get_current_keys(self) -> dict:
        """Get the current encryption keys."""
        return self.state.current_keys
    
    def check_rotation_needed(self) -> bool:
        """Check if key rotation is due."""
        return time.time() >= self.state.rotation_due
    
    def get_time_until_rotation(self) -> float:
        """Get seconds until next rotation."""
        return max(0, self.state.rotation_due - time.time())
    
    def prepare_next_keys(self) -> dict:
        """
        Generate the next set of keys from next_key_seed.
        
        Returns:
            New key dictionary
        """
        # Use next_key_seed to derive new keys
        seed = self.state.current_keys['next_key_seed']
        new_timestamp = int(time.time())
        
        # Create new connection context
        new_connection_id = f"{self.connection_id}-{new_timestamp}"
        
        # Derive new keys from seed
        new_keys = derive_session_keys(seed, new_connection_id, new_timestamp)
        
        self.state.next_keys = new_keys
        return new_keys
    
    def perform_rotation(self):
        """Perform the key rotation."""
        if not self.state.next_keys:
            self.prepare_next_keys()
        
        # Save old keys to history
        self._key_history.append({
            'timestamp': time.time(),
            'keys': self.state.current_keys
        })
        
        # Limit history size
        if len(self._key_history) > 5:
            self._key_history.pop(0)
        
        # Rotate keys
        old_keys = self.state.current_keys
        self.state.current_keys = self.state.next_keys
        self.state.next_keys = None
        
        # Update rotation schedule
        now = time.time()
        self.state.rotation_due = now + self.ROTATION_INTERVAL
        self.state.grace_period_end = now + self.GRACE_PERIOD
        
        # Notify callback
        if self.on_rotation:
            self.on_rotation(old_keys, self.state.current_keys)
        
        print(f"[KeyRotator] Keys rotated. Next rotation in {self.ROTATION_INTERVAL}s")
    
    def create_rotation_message(self) -> dict:
        """
        Create a key rotation message to send to peer.
        
        Returns:
            Message dictionary
        """
        if not self.state.next_keys:
            self.prepare_next_keys()
        
        import base64
        
        return {
            'type': 'key_rotation',
            'version': '2.0',
            'timestamp': int(time.time()),
            'connection_id': self.connection_id,
            'next_encryption_key': base64.b64encode(
                self.state.next_keys['encryption_key']
            ).decode('ascii'),
            'next_mac_key': base64.b64encode(
                self.state.next_keys['mac_key']
            ).decode('ascii'),
            'next_iv_key': base64.b64encode(
                self.state.next_keys['iv_key']
            ).decode('ascii'),
            'rotation_time': int(self.state.rotation_due)
        }
    
    def handle_rotation_message(self, message: dict) -> bool:
        """
        Handle a key rotation message from peer.
        
        Args:
            message: Rotation message from peer
            
        Returns:
            True if rotation was successful
        """
        try:
            import base64
            
            # Validate message
            if message.get('type') != 'key_rotation':
                return False
            
            if message.get('version') != '2.0':
                return False
            
            # Decode keys
            next_keys = {
                'encryption_key': base64.b64decode(message['next_encryption_key']),
                'mac_key': base64.b64decode(message['next_mac_key']),
                'iv_key': base64.b64decode(message['next_iv_key']),
                'next_key_seed': secrets.token_bytes(32)  # Generate new seed
            }
            
            self.state.next_keys = next_keys
            
            # Perform rotation
            self.perform_rotation()
            
            return True
            
        except Exception as e:
            print(f"[KeyRotator] Failed to handle rotation message: {e}")
            return False
    
    def force_rotation(self):
        """Force immediate key rotation (for Compromised Protocol)."""
        self.prepare_next_keys()
        self.perform_rotation()
    
    def destroy_keys(self):
        """Destroy all keys (for Compromised Protocol)."""
        self.state.current_keys = None
        self.state.next_keys = None
        self._key_history = []
        self.state.rotation_due = float('inf')
        print("[KeyRotator] All keys destroyed")


# Example usage
if __name__ == "__main__":
    import secrets
    
    def on_rotation(old_keys, new_keys):
        print("Key rotation callback triggered")
    
    # Create rotator
    shared_secret = secrets.token_bytes(32)
    rotator = KeyRotator(shared_secret, "conn-123", on_rotation)
    
    print(f"Time until rotation: {rotator.get_time_until_rotation():.0f}s")
    
    # Simulate rotation
    next_keys = rotator.prepare_next_keys()
    print(f"Prepared next keys: {list(next_keys.keys())}")
    
    # Create rotation message
    msg = rotator.create_rotation_message()
    print(f"Rotation message type: {msg['type']}")
    
    # Perform rotation
    rotator.perform_rotation()
    print(f"Keys after rotation: {list(rotator.get_current_keys().keys())}")
