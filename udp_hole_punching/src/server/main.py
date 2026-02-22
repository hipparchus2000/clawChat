"""
ClawChat UDP Hole Punching Server.

Dark server that:
- Generates security files for initial connection
- Listens for UDP hole punch attempts
- Handles encrypted communication
- Implements port rotation
- Supports Compromised Protocol
"""

import os
import sys
import time
import socket
import signal
import secrets
import argparse
from pathlib import Path
from typing import Optional, Tuple

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.security.encryption import CryptoManager, derive_session_keys
from src.security.key_rotation import KeyRotator
from src.security.file_manager import SecurityFileManager
from src.networking.udp_hole_punch import UDPHolePuncher, HolePunchState
from src.protocol.compromised import CompromisedProtocolHandler
from src.protocol.messages import MessageHandler, MessageType, Message
from src.server.file_generator import SecurityFileGenerator


class ClawChatServer:
    """
    ClawChat UDP Hole Punching Server.
    
    Runs as a dark server (no open ports until hole punch).
    """
    
    def __init__(
        self,
        security_directory: str,
        bootstrap_key: bytes,
        server_ip: str,
        server_port: int = None,
        server_id: str = "clawchat-server"
    ):
        """
        Initialize server.
        
        Args:
            security_directory: Directory for security files
            bootstrap_key: Key for encrypting security files
            server_ip: Server public IP
            server_port: Server UDP port (random if None)
            server_id: Unique server identifier
        """
        self.security_directory = security_directory
        self.bootstrap_key = bootstrap_key
        self.server_ip = server_ip
        self.server_port = server_port or self._select_random_port()
        self.server_id = server_id
        
        # Components
        self.file_generator = SecurityFileGenerator(
            security_directory,
            bootstrap_key,
            server_id
        )
        self.file_generator.set_server_info(server_ip, self.server_port)
        
        self.crypto: Optional[CryptoManager] = None
        self.key_rotator: Optional[KeyRotator] = None
        self.compromised_handler: Optional[CompromisedProtocolHandler] = None
        
        # State
        self.running = False
        self.socket: Optional[socket.socket] = None
        self.shared_secret: Optional[bytes] = None
        self.connection_id: Optional[str] = None
        self.peer_address: Optional[Tuple[str, int]] = None
        
        # Stats
        self.messages_received = 0
        self.messages_sent = 0
        self.start_time = 0.0
    
    def _select_random_port(self) -> int:
        """Select a random available port."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(('0.0.0.0', 0))
        port = sock.getsockname()[1]
        sock.close()
        return port
    
    def _on_key_rotation(self, old_keys, new_keys):
        """Callback for key rotation."""
        print(f"[Server] Keys rotated")
        if self.crypto:
            self.crypto.set_session_keys(new_keys)
    
    def _on_keys_destroyed(self):
        """Callback for Compromised Protocol."""
        print("[Server] Keys destroyed by Compromised Protocol")
        self.running = False
    
    def _on_new_file_generated(self):
        """Callback to generate new security file after compromise."""
        print("[Server] Generating new security file...")
        filepath = self.file_generator.generate_file()
        print(f"[Server] New file ready: {filepath}")
        print("[Server] USER ACTION REQUIRED: Transfer this file to client securely")
    
    def generate_initial_security_file(self) -> str:
        """Generate initial security file for client."""
        filepath = self.file_generator.generate_file()
        self.shared_secret = self.file_generator.get_current_secret()
        return filepath
    
    def start(self):
        """Start the server."""
        print(f"\n{'='*60}")
        print(f"  ClawChat UDP Hole Punching Server v2.0")
        print(f"{'='*60}\n")
        
        # Generate or load security file
        if not self.shared_secret:
            filepath = self.generate_initial_security_file()
            print(f"[Server] Security file created: {filepath}")
            print(f"[Server] Transfer this file to client securely")
        
        # Setup crypto
        self.connection_id = f"{self.server_id}-{int(time.time())}"
        self.crypto = CryptoManager()
        
        # Derive initial session keys
        keys = derive_session_keys(
            self.shared_secret,
            self.connection_id,
            int(time.time())
        )
        self.crypto.set_session_keys(keys)
        
        # Setup key rotator
        self.key_rotator = KeyRotator(
            self.shared_secret,
            self.connection_id,
            on_rotation=self._on_key_rotation
        )
        
        # Setup compromised handler
        self.compromised_handler = CompromisedProtocolHandler(
            is_server=True,
            connection_id=self.connection_id,
            mac_key=keys['mac_key'],
            on_keys_destroyed=self._on_keys_destroyed,
            on_new_file_generated=self._on_new_file_generated
        )
        
        # Create socket
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(('0.0.0.0', self.server_port))
        self.socket.settimeout(1.0)  # 1 second timeout for recv
        
        print(f"[Server] Listening on UDP {self.server_ip}:{self.server_port}")
        print(f"[Server] Waiting for hole punch...")
        print(f"[Server] Press Ctrl+C to stop\n")
        
        self.running = True
        self.start_time = time.time()
        
        # Main loop
        try:
            while self.running:
                self._process_loop()
        except KeyboardInterrupt:
            print("\n[Server] Stopping...")
        finally:
            self.stop()
    
    def _process_loop(self):
        """Main processing loop."""
        # Check for key rotation
        if self.key_rotator and self.key_rotator.check_rotation_needed():
            print("[Server] Key rotation due")
            msg = self.key_rotator.create_rotation_message()
            self._send_message(MessageType.KEY_ROTATION, msg)
            self.key_rotator.perform_rotation()
        
        # Check for compromised state
        if self.compromised_handler and self.compromised_handler.is_compromised():
            print("[Server] Connection compromised, shutting down")
            self.running = False
            return
        
        # Receive data
        try:
            data, addr = self.socket.recvfrom(2048)
            self._handle_packet(data, addr)
        except socket.timeout:
            pass
        except Exception as e:
            print(f"[Server] Receive error: {e}")
    
    def _handle_packet(self, data: bytes, addr: Tuple[str, int]):
        """Handle incoming packet."""
        # Try to decrypt
        try:
            plaintext = self.crypto.decrypt_packet(data)
        except Exception:
            # Failed to decrypt - might be punch packet or garbage
            return
        
        # Parse message
        msg = Message.from_bytes(plaintext)
        self.messages_received += 1
        
        # Update peer address
        if not self.peer_address:
            self.peer_address = addr
            print(f"[Server] Peer connected: {addr}")
        
        # Handle message types
        if msg.msg_type == MessageType.CHAT:
            self._handle_chat(msg, addr)
        elif msg.msg_type == MessageType.KEEPALIVE:
            self._handle_keepalive(msg, addr)
        elif msg.msg_type == MessageType.KEY_ROTATION:
            self._handle_key_rotation(msg, addr)
        elif msg.msg_type == MessageType.COMPROMISED:
            self._handle_compromised(msg, addr)
        elif msg.msg_type == MessageType.PUNCH:
            self._handle_punch(msg, addr)
        else:
            print(f"[Server] Unknown message type: {msg.msg_type}")
    
    def _handle_chat(self, msg: Message, addr):
        """Handle chat message."""
        text = msg.payload.get('text', '')
        sender = msg.payload.get('sender', 'unknown')
        print(f"[Chat] {sender}: {text}")
        
        # Echo back
        self._send_message(MessageType.CHAT, {
            'text': f"Echo: {text}",
            'sender': 'server'
        })
    
    def _handle_keepalive(self, msg: Message, addr):
        """Handle keepalive."""
        self._send_message(MessageType.KEEPALIVE, {'pong': True})
    
    def _handle_key_rotation(self, msg: Message, addr):
        """Handle key rotation message."""
        print("[Server] Received key rotation from client")
        # Keys are already rotated by KeyRotator
    
    def _handle_compromised(self, msg: Message, addr):
        """Handle compromised signal."""
        print("[Server] Received COMPROMISED signal")
        
        if self.compromised_handler.handle_compromised_signal(msg.payload):
            # Send ACK
            ack = self.compromised_handler.create_ack_signal(new_file_ready=True)
            self._send_message(MessageType.COMPROMISED_ACK, ack)
    
    def _handle_punch(self, msg: Message, addr):
        """Handle punch packet."""
        # Send punch ACK
        self._send_message(MessageType.PUNCH_ACK, {'status': 'ok'})
        print(f"[Server] Punch from {addr} acknowledged")
    
    def _send_message(self, msg_type: MessageType, payload: dict):
        """Send encrypted message to peer."""
        if not self.peer_address:
            return
        
        msg = Message(msg_type=msg_type, payload=payload)
        plaintext = msg.to_bytes()
        
        encrypted = self.crypto.encrypt_packet(plaintext)
        
        try:
            self.socket.sendto(encrypted, self.peer_address)
            self.messages_sent += 1
        except Exception as e:
            print(f"[Server] Send error: {e}")
    
    def stop(self):
        """Stop the server."""
        self.running = False
        
        if self.socket:
            self.socket.close()
        
        runtime = time.time() - self.start_time
        print(f"\n[Server] Stopped")
        print(f"[Server] Runtime: {runtime:.1f}s")
        print(f"[Server] Messages received: {self.messages_received}")
        print(f"[Server] Messages sent: {self.messages_sent}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='ClawChat UDP Server')
    parser.add_argument('--ip', default='0.0.0.0', help='Server IP')
    parser.add_argument('--port', type=int, default=None, help='Server port (random if not set)')
    parser.add_argument('--security-dir', default='/home/openclaw/clawchat/security',
                        help='Security files directory')
    parser.add_argument('--bootstrap-key', default=None, help='Bootstrap key (base64)')
    
    args = parser.parse_args()
    
    # Get or generate bootstrap key
    if args.bootstrap_key:
        import base64
        bootstrap_key = base64.b64decode(args.bootstrap_key)
    else:
        # Use environment variable or default
        bootstrap_key = os.environ.get(
            'CLAWCHAT_BOOTSTRAP_KEY',
            'bootstrap-key-32bytes-long-for-dev-only!'
        ).encode()[:32]
    
    # Create server
    server = ClawChatServer(
        security_directory=args.security_dir,
        bootstrap_key=bootstrap_key,
        server_ip=args.ip,
        server_port=args.port
    )
    
    # Start
    server.start()


if __name__ == "__main__":
    main()
