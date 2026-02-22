"""
ClawChat UDP Hole Punching Client.

Features:
- File browser for selecting security files
- UDP hole punching to server
- Encrypted communication
- Compromised Protocol support
- Tkinter GUI interface
"""

import os
import sys
import time
import socket
import signal
import argparse
import threading
from pathlib import Path
from typing import Optional, Tuple

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.security.encryption import CryptoManager, derive_session_keys
from src.security.key_rotation import KeyRotator
from src.security.file_manager import SecurityFileManager, SecurityFile
from src.networking.udp_hole_punch import UDPHolePuncher
from src.networking.nat_detection import NATDetector, NATType
from src.protocol.compromised import CompromisedProtocolHandler
from src.protocol.messages import MessageHandler, MessageType, Message
from src.client.file_browser import select_security_file


class ClawChatClient:
    """
    ClawChat UDP Hole Punching Client.
    
    Connects to server using security file and UDP hole punching.
    """
    
    def __init__(self, bootstrap_key: bytes = None):
        """
        Initialize client.
        
        Args:
            bootstrap_key: Key for decrypting security files
        """
        self.bootstrap_key = bootstrap_key
        
        # Components
        self.crypto: Optional[CryptoManager] = None
        self.key_rotator: Optional[KeyRotator] = None
        self.compromised_handler: Optional[CompromisedProtocolHandler] = None
        self.hole_puncher: Optional[UDPHolePuncher] = None
        
        # State
        self.running = False
        self.socket: Optional[socket.socket] = None
        self.security_file: Optional[SecurityFile] = None
        self.shared_secret: Optional[bytes] = None
        self.connection_id: Optional[str] = None
        self.server_address: Optional[Tuple[str, int]] = None
        
        # Stats
        self.messages_received = 0
        self.messages_sent = 0
        self.start_time = 0.0
    
    def _on_key_rotation(self, old_keys, new_keys):
        """Callback for key rotation."""
        print(f"[Client] Keys rotated")
        if self.crypto:
            self.crypto.set_session_keys(new_keys)
    
    def _on_keys_destroyed(self):
        """Callback for Compromised Protocol."""
        print("[Client] Keys destroyed by Compromised Protocol")
        print("[Client] Connection terminated. Please obtain new security file.")
        self.running = False
    
    def load_security_file(self, filepath: str) -> bool:
        """
        Load and validate security file.
        
        Args:
            filepath: Path to security file
            
        Returns:
            True if successful
        """
        try:
            import base64
            
            manager = SecurityFileManager(bootstrap_key=self.bootstrap_key)
            self.security_file = manager.load_security_file(filepath)
            
            # Check validity
            if not self.security_file.is_valid():
                print(f"[Client] Security file expired!")
                return False
            
            # Decode shared secret
            self.shared_secret = base64.b64decode(self.security_file.shared_secret)
            
            # Set server address
            self.server_address = (
                self.security_file.server_public_ip,
                self.security_file.server_udp_port
            )
            
            print(f"[Client] Security file loaded")
            print(f"[Client] Server: {self.server_address[0]}:{self.server_address[1]}")
            print(f"[Client] Valid for: {self.security_file.time_until_expiry()}s")
            
            return True
            
        except Exception as e:
            print(f"[Client] Failed to load security file: {e}")
            return False
    
    def detect_nat(self) -> NATType:
        """Detect NAT type."""
        print("[Client] Detecting NAT type...")
        detector = NATDetector()
        nat_type = detector.detect()
        
        strategy = detector.get_hole_punch_strategy(nat_type)
        print(f"[Client] NAT type: {nat_type.value}")
        print(f"[Client] Strategy: {strategy['description']}")
        print(f"[Client] Expected success: {strategy['success_rate']*100:.0f}%")
        
        return nat_type
    
    def connect(self) -> bool:
        """
        Connect to server using UDP hole punching.
        
        Returns:
            True if connected
        """
        if not self.security_file:
            print("[Client] No security file loaded")
            return False
        
        # Setup crypto
        self.connection_id = self.security_file.connection_id
        self.crypto = CryptoManager()
        
        # Derive session keys
        keys = derive_session_keys(
            self.shared_secret,
            self.connection_id,
            self.security_file.timestamp
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
            is_server=False,
            connection_id=self.connection_id,
            mac_key=keys['mac_key'],
            on_keys_destroyed=self._on_keys_destroyed
        )
        
        # Detect NAT
        nat_type = self.detect_nat()
        
        if nat_type == NATType.BLOCKED:
            print("[Client] Cannot connect: UDP appears to be blocked")
            return False
        
        # Perform hole punching
        print(f"\n[Client] Attempting hole punch to {self.server_address[0]}:{self.server_address[1]}...")
        
        self.hole_puncher = UDPHolePuncher(
            crypto_manager=self.crypto,
            timeout=60.0,
            retry_interval=0.5
        )
        
        result = self.hole_puncher.punch(
            target_ip=self.server_address[0],
            target_port=self.server_address[1]
        )
        
        if result.success:
            self.socket = result.socket
            print(f"[Client] Connected! Latency: {result.latency_ms:.1f}ms")
            print(f"[Client] Local port: {self.hole_puncher.local_port}")
            return True
        else:
            print(f"[Client] Hole punching failed: {result.error_message}")
            return False
    
    def start(self):
        """Start the client."""
        print(f"\n{'='*60}")
        print(f"  ClawChat UDP Hole Punching Client v2.0")
        print(f"{'='*60}\n")
        
        # Select security file
        print("[Client] Please select security file...")
        filepath = select_security_file(use_gui=True)
        
        if not filepath:
            print("[Client] No file selected. Exiting.")
            return
        
        # Load security file
        if not self.load_security_file(filepath):
            print("[Client] Failed to load security file. Exiting.")
            return
        
        # Connect
        if not self.connect():
            print("[Client] Failed to connect. Exiting.")
            return
        
        print(f"\n[Client] Starting main loop...")
        print("[Client] Commands:")
        print("  /quit - Exit")
        print("  /compromised - Trigger Compromised Protocol")
        print("  <any text> - Send chat message\n")
        
        self.running = True
        self.start_time = time.time()
        
        # Start receive thread
        recv_thread = threading.Thread(target=self._receive_loop, daemon=True)
        recv_thread.start()
        
        # Main input loop
        try:
            while self.running:
                try:
                    text = input("> ").strip()
                    
                    if not text:
                        continue
                    
                    if text == "/quit":
                        self.running = False
                        break
                    
                    if text == "/compromised":
                        self._trigger_compromised()
                        continue
                    
                    # Send chat message
                    self._send_chat(text)
                    
                except EOFError:
                    break
                except KeyboardInterrupt:
                    break
                    
        finally:
            self.stop()
    
    def _receive_loop(self):
        """Background receive loop."""
        while self.running:
            try:
                self.socket.settimeout(1.0)
                data, addr = self.socket.recvfrom(2048)
                self._handle_packet(data, addr)
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"[Client] Receive error: {e}")
    
    def _handle_packet(self, data: bytes, addr: Tuple[str, int]):
        """Handle incoming packet."""
        try:
            plaintext = self.crypto.decrypt_packet(data)
            msg = Message.from_bytes(plaintext)
            self.messages_received += 1
            
            # Handle message types
            if msg.msg_type == MessageType.CHAT:
                text = msg.payload.get('text', '')
                sender = msg.payload.get('sender', 'server')
                print(f"\n[{sender}] {text}")
                print("> ", end='', flush=True)
                
            elif msg.msg_type == MessageType.KEEPALIVE:
                pass  # Keepalive received
                
            elif msg.msg_type == MessageType.KEY_ROTATION:
                print("\n[Client] Key rotation received")
                print("> ", end='', flush=True)
                
            elif msg.msg_type == MessageType.COMPROMISED_ACK:
                print("\n[Client] Compromised ACK received")
                if self.compromised_handler:
                    self.compromised_handler.handle_ack_signal(msg.payload)
                    
            elif msg.msg_type == MessageType.ERROR:
                error = msg.payload.get('message', 'Unknown error')
                print(f"\n[Error] {error}")
                print("> ", end='', flush=True)
                
        except Exception as e:
            pass  # Failed to decrypt - ignore
    
    def _send_chat(self, text: str):
        """Send chat message."""
        msg = MessageHandler.create_chat_message(text, "client")
        self._send_message(msg)
    
    def _send_message(self, msg: Message):
        """Send encrypted message."""
        try:
            plaintext = msg.to_bytes()
            encrypted = self.crypto.encrypt_packet(plaintext)
            self.socket.sendto(encrypted, self.server_address)
            self.messages_sent += 1
        except Exception as e:
            print(f"[Client] Send error: {e}")
    
    def _trigger_compromised(self):
        """Trigger Compromised Protocol."""
        print("\n[Client] TRIGGERING COMPROMISED PROTOCOL")
        print("[Client] This will destroy all keys on both sides!")
        
        confirm = input("Type 'YES' to confirm: ").strip()
        
        if confirm == "YES":
            signal = self.compromised_handler.create_compromised_signal(
                reason="user_initiated"
            )
            self._send_message(Message(
                msg_type=MessageType.COMPROMISED,
                payload=signal
            ))
            print("[Client] Compromised signal sent")
            print("[Client] Waiting for server ACK...")
        else:
            print("[Client] Cancelled")
    
    def stop(self):
        """Stop the client."""
        self.running = False
        
        if self.socket:
            self.socket.close()
        
        runtime = time.time() - self.start_time
        print(f"\n[Client] Stopped")
        print(f"[Client] Runtime: {runtime:.1f}s")
        print(f"[Client] Messages received: {self.messages_received}")
        print(f"[Client] Messages sent: {self.messages_sent}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='ClawChat UDP Client')
    parser.add_argument('--bootstrap-key', default=None, help='Bootstrap key (base64)')
    parser.add_argument('--file', default=None, help='Security file path (skip GUI)')
    
    args = parser.parse_args()
    
    # Get or generate bootstrap key
    if args.bootstrap_key:
        import base64
        bootstrap_key = base64.b64decode(args.bootstrap_key)
    else:
        bootstrap_key = os.environ.get(
            'CLAWCHAT_BOOTSTRAP_KEY',
            'bootstrap-key-32bytes-long-for-dev-only!'
        ).encode()[:32]
    
    # Create client
    client = ClawChatClient(bootstrap_key=bootstrap_key)
    
    # If file specified, skip GUI
    if args.file:
        if not client.load_security_file(args.file):
            print("Failed to load security file")
            sys.exit(1)
        if not client.connect():
            print("Failed to connect")
            sys.exit(1)
        # TODO: Start chat loop directly
    
    # Start
    client.start()


if __name__ == "__main__":
    main()
