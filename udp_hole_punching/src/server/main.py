"""
ClawChat UDP Hole Punching Server.

Dark server that:
- Generates security files for initial connection
- Listens for UDP hole punch attempts
- Handles encrypted communication
- Relays messages to LLM Server
- Implements port rotation
- Supports Compromised Protocol

Architecture:
    GUI Client ←→ Hole Punching Server ←→ LLM Server
    (public)       (public)              (localhost)
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
    
    # Default LLM server port
    DEFAULT_LLM_PORT = 55556
    
    
    def _send_to_llm_tcp(self, msg: Message) -> Optional[Message]:
        """Send message to LLM server over TCP and wait for response."""
        if not self.llm_socket:
            if not self._connect_to_llm_server():
                return None
        
        try:
            # Send message
            self.llm_socket.send(msg.to_bytes())
            
            # Wait for response (longer timeout for AI processing)
            self.llm_socket.settimeout(60.0)
            
            # Receive response
            data = self.llm_socket.recv(8192)
            if not data:
                print("[Server] LLM server closed connection")
                self.llm_socket.close()
                self.llm_socket = None
                return None
            
            response = Message.from_bytes(data)
            return response
            
        except socket.timeout:
            print("[Server] LLM response timeout")
            return None
        except ConnectionError as e:
            print(f"[Server] LLM connection error: {e}")
            self.llm_socket.close()
            self.llm_socket = None
            return None
        except Exception as e:
            print(f"[Server] LLM communication error: {e}")
            self.llm_socket.close()
            self.llm_socket = None
            return None

    def __init__(
        self,
        security_directory: str,
        bootstrap_key: bytes,
        server_ip: str,
        server_port: int = None,
        server_id: str = "clawchat-server",
        llm_server_ip: str = "127.0.0.1",
        llm_server_port: int = None
    ):
        """
        Initialize server.
        
        Args:
            security_directory: Directory for security files
            bootstrap_key: Key for encrypting security files
            server_ip: Server public IP
            server_port: Server UDP port (random if None)
            server_id: Unique server identifier
            llm_server_ip: LLM server IP (default: localhost)
            llm_server_port: LLM server port (default: 55556)
        """
        self.security_directory = security_directory
        self.bootstrap_key = bootstrap_key
        self.server_ip = server_ip
        self.server_port = server_port or self._select_random_port()
        self.server_id = server_id
        self.llm_server_ip = llm_server_ip
        self.llm_server_port = llm_server_port or self.DEFAULT_LLM_PORT
        
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
        
        # LLM relay socket
        self.llm_socket: Optional[socket.socket] = None
        
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
    
    def _connect_to_llm(self) -> bool:
        """
        Connect to LLM server.
        
        Returns:
            True if connection successful
        """
        print(f"[Server] Connecting to LLM server at {self.llm_server_ip}:{self.llm_server_port}...")
        try:
            self.llm_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.llm_socket.settimeout(2.0)
            
            # Try multiple times (LLM server might still be starting)
            for attempt in range(3):
                try:
                                # Test connection by sending ping
            try:
                # Connect to LLM server (TCP)
                self.llm_socket.connect((self.llm_server_ip, self.llm_server_port))
                self.llm_socket.settimeout(2.0)
                
                # Send ping
                ping_msg = Message(MessageType.KEEPALIVE, {'ping': True})
                self.llm_socket.send(ping_msg.to_bytes())
                
                # Wait for pong
                data = self.llm_socket.recv(1024)
                response = Message.from_bytes(data)
                if response.msg_type == MessageType.KEEPALIVE:
                    print(f"[Server] LLM connection established")
                    return True
            except socket.timeout:
                print(f"[Server] LLM ping attempt {attempt + 1}/3...")
                time.sleep(0.5)
                continue
            except ConnectionRefusedError:
                print(f"[Server] LLM server not ready...")
                time.sleep(0.5)
                continue
                except socket.timeout:
                    print(f"[Server] LLM ping attempt {attempt + 1}/3...")
                    time.sleep(0.5)
                    continue
            
            print(f"[Server] Could not reach LLM server after 3 attempts")
            return False
            
        except Exception as e:
            print(f"[Server] LLM connection error: {e}")
            return False
    
    def _relay_to_llm(self, msg: Message) -> Optional[Message]:
        """
        Relay message to LLM server and return response.
        
        Args:
            msg: Message to relay
            
        Returns:
            Response message from LLM, or None on error
        """
        if not self.llm_socket:
            return None
        
        try:
            # Send to LLM server
            self.llm_socket.sendto(msg.to_bytes(),
                                  (self.llm_server_ip, self.llm_server_port))
            
            # Wait for response (with timeout)
            self.llm_socket.settimeout(60.0)  # 60s for AI processing
            data, _ = self.llm_socket.recvfrom(8192)
            
            response = Message.from_bytes(data)
            return response
            
        except socket.timeout:
            print("[Server] LLM timeout")
            return None
        except Exception as e:
            print(f"[Server] LLM relay error: {e}")
            return None
    
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
        
        # Connect to LLM server (REQUIRED)
        print(f"[Server] Connecting to LLM server at {self.llm_server_ip}:{self.llm_server_port}...")
        if not self._connect_to_llm():
            print("[Server] ERROR: Cannot reach LLM server")
            print("[Server] Please ensure LLM server is running:")
            print("    python run_llm_server.py")
            return
        print("[Server] Connected to LLM server")
        
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
        elif msg.msg_type in (MessageType.FILE_LIST, MessageType.FILE_DOWNLOAD, 
                              MessageType.FILE_UPLOAD, MessageType.FILE_DELETE,
                              MessageType.FILE_RENAME, MessageType.FILE_MKDIR,
                              MessageType.CRON_LIST, MessageType.CRON_RUN, 
                              MessageType.CRON_RELOAD, MessageType.CRON_ADD,
                              MessageType.CRON_REMOVE, MessageType.CRON_RESULT):
            self._handle_relay(msg, addr)
        else:
            print(f"[Server] Unknown message type: {msg.msg_type}")
    
    def _handle_chat(self, msg: Message, addr):
        """Handle chat message - relay to LLM server."""
        text = msg.payload.get('text', '')
        sender = msg.payload.get('sender', 'unknown')
        print(f"[Chat] {sender}: {text}")
        
        # Relay to LLM server
        response = self._relay_to_llm(msg)
        
        if response:
            # Forward LLM response to client
            self._send_message(response.msg_type, response.payload)
            response_text = response.payload.get('text', '')
            print(f"[Chat] Assistant: {response_text[:80]}...")
        else:
            # Error talking to LLM
            self._send_message(MessageType.CHAT, {
                'text': '[Error: Cannot reach LLM server]',
                'sender': 'system'
            })
    
    def _handle_keepalive(self, msg: Message, addr):
        """Handle keepalive."""
        self._send_message(MessageType.KEEPALIVE, {'pong': True})
    
    def _handle_relay(self, msg: Message, addr):
        """Relay file/cron messages to LLM server."""
        response = self._relay_to_llm(msg)
        if response:
            self._send_message(response.msg_type, response.payload)
        else:
            self._send_message(msg.msg_type, {
                'success': False,
                'error': 'Cannot reach LLM server'
            })
    
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
        
        if self.llm_socket:
            self.llm_socket.close()
        
        runtime = time.time() - self.start_time
        print(f"\n[Server] Stopped")
        print(f"[Server] Runtime: {runtime:.1f}s")
        print(f"[Server] Messages received: {self.messages_received}")
        print(f"[Server] Messages sent: {self.messages_sent}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='ClawChat UDP Hole Punching Server')
    parser.add_argument('--ip', default='0.0.0.0', help='Server IP')
    parser.add_argument('--port', type=int, default=None, help='Server port (random if not set)')
    parser.add_argument('--security-dir', default='/home/openclaw/clawchat/security',
                        help='Security files directory')
    parser.add_argument('--bootstrap-key', default=None, help='Bootstrap key (base64)')
    parser.add_argument('--llm-ip', default='127.0.0.1', help='LLM server IP')
    parser.add_argument('--llm-port', type=int, default=55556, help='LLM server port')
    
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
        server_port=args.port,
        llm_server_ip=args.llm_ip,
        llm_server_port=args.llm_port
    )
    
    # Start
    server.start()


if __name__ == "__main__":
    main()
