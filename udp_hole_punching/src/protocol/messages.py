"""
Message protocol for ClawChat.

Defines message types and handles message encoding/decoding.
"""

import json
import struct
import time
from enum import IntEnum
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict


class MessageType(IntEnum):
    """Message type enumeration."""
    # Connection
    PUNCH = 0x01
    PUNCH_ACK = 0x02
    KEEPALIVE = 0x03
    
    # Data
    CHAT = 0x10
    FILE_OFFER = 0x11
    FILE_DATA = 0x12
    FILE_ACK = 0x13
    
    # Control
    KEY_ROTATION = 0x20
    PORT_ROTATION = 0x21
    ERROR = 0x22
    
    # Security
    COMPROMISED = 0x30
    COMPROMISED_ACK = 0x31


@dataclass
class Message:
    """Base message structure."""
    msg_type: MessageType
    payload: Dict[str, Any]
    timestamp: float = 0
    message_id: str = ""
    
    def __post_init__(self):
        if self.timestamp == 0:
            self.timestamp = time.time()
        if not self.message_id:
            import secrets
            self.message_id = secrets.token_hex(8)
    
    def to_bytes(self) -> bytes:
        """Convert to bytes for transmission."""
        # Format: [type:1][timestamp:8][id_len:1][id][payload_len:4][payload]
        payload_json = json.dumps(self.payload).encode('utf-8')
        msg_id_bytes = self.message_id.encode('utf-8')
        
        header = struct.pack(
            '!BdB',
            self.msg_type,
            self.timestamp,
            len(msg_id_bytes)
        )
        
        payload_header = struct.pack('!I', len(payload_json))
        
        return header + msg_id_bytes + payload_header + payload_json
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'Message':
        """Parse message from bytes."""
        # Parse header: [type:1][timestamp:8][id_len:1]
        msg_type = struct.unpack('!B', data[0:1])[0]
        timestamp = struct.unpack('!d', data[1:9])[0]
        id_len = struct.unpack('!B', data[9:10])[0]
        
        msg_id = data[10:10+id_len].decode('utf-8')
        
        payload_len = struct.unpack('!I', data[10+id_len:14+id_len])[0]
        payload_json = data[14+id_len:14+id_len+payload_len]
        payload = json.loads(payload_json.decode('utf-8'))
        
        return cls(
            msg_type=MessageType(msg_type),
            payload=payload,
            timestamp=timestamp,
            message_id=msg_id
        )
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps({
            'type': self.msg_type.value,
            'type_name': self.msg_type.name,
            'payload': self.payload,
            'timestamp': self.timestamp,
            'message_id': self.message_id
        }, indent=2)


class MessageHandler:
    """Handles message encoding/decoding."""
    
    @staticmethod
    def create_chat_message(text: str, sender: str) -> Message:
        """Create a chat message."""
        return Message(
            msg_type=MessageType.CHAT,
            payload={
                'text': text,
                'sender': sender
            }
        )
    
    @staticmethod
    def create_keepalive() -> Message:
        """Create a keepalive message."""
        return Message(
            msg_type=MessageType.KEEPALIVE,
            payload={'ping': True}
        )
    
    @staticmethod
    def create_error(error_code: int, error_message: str) -> Message:
        """Create an error message."""
        return Message(
            msg_type=MessageType.ERROR,
            payload={
                'code': error_code,
                'message': error_message
            }
        )
    
    @staticmethod
    def create_key_rotation(keys: Dict[str, str]) -> Message:
        """Create a key rotation message."""
        return Message(
            msg_type=MessageType.KEY_ROTATION,
            payload=keys
        )
    
    @staticmethod
    def parse_message(data: bytes) -> Optional[Message]:
        """Parse a message from bytes."""
        try:
            return Message.from_bytes(data)
        except Exception as e:
            print(f"Failed to parse message: {e}")
            return None


# Example usage
if __name__ == "__main__":
    print("Message Protocol Example")
    print("=" * 50)
    
    # Create messages
    chat = MessageHandler.create_chat_message("Hello!", "Alice")
    print(f"Chat message: {chat.to_json()}")
    
    # Convert to bytes and back
    data = chat.to_bytes()
    print(f"Serialized size: {len(data)} bytes")
    
    parsed = Message.from_bytes(data)
    print(f"Parsed message type: {parsed.msg_type.name}")
    print(f"Payload: {parsed.payload}")
