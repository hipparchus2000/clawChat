"""
UDP Hole Punching implementation for ClawChat.

Establishes direct P2P connections through NAT using UDP hole punching.
"""

import socket
import time
import struct
import secrets
from dataclasses import dataclass
from typing import Optional, Callable, Tuple
from enum import Enum

from ..security.encryption import CryptoManager


class HolePunchState(Enum):
    """Hole punching state machine."""
    IDLE = "idle"
    PREPARING = "preparing"
    PUNCHING = "punching"
    CONNECTED = "connected"
    FAILED = "failed"


@dataclass
class HolePunchResult:
    """Result of hole punching attempt."""
    success: bool
    socket: Optional[socket.socket]
    peer_address: Optional[Tuple[str, int]]
    latency_ms: float
    attempts: int
    error_message: Optional[str] = None


class UDPHolePuncher:
    """
    Implements UDP hole punching algorithm.
    
    Uses encrypted packets for security.
    """
    
    # Packet types
    PKT_PUNCH = 0x01
    PKT_PUNCH_ACK = 0x02
    PKT_KEEPALIVE = 0x03
    PKT_DATA = 0x04
    
    def __init__(
        self,
        crypto_manager: CryptoManager,
        timeout: float = 60.0,
        retry_interval: float = 0.5,
        on_state_change: Optional[Callable] = None
    ):
        """
        Initialize hole puncher.
        
        Args:
            crypto_manager: For encrypting/decrypting packets
            timeout: Total timeout for hole punching
            retry_interval: Interval between punch attempts
            on_state_change: Callback for state changes
        """
        self.crypto = crypto_manager
        self.timeout = timeout
        self.retry_interval = retry_interval
        self.on_state_change = on_state_change
        
        self.state = HolePunchState.IDLE
        self.socket: Optional[socket.socket] = None
        self.local_port: Optional[int] = None
    
    def _set_state(self, new_state: HolePunchState):
        """Update state and notify."""
        old_state = self.state
        self.state = new_state
        if self.on_state_change:
            self.on_state_change(old_state, new_state)
        print(f"[HolePunch] State: {old_state.value} -> {new_state.value}")
    
    def _create_socket(self, preferred_port: Optional[int] = None) -> socket.socket:
        """Create and configure UDP socket."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        if preferred_port:
            try:
                sock.bind(('0.0.0.0', preferred_port))
            except OSError:
                sock.bind(('0.0.0.0', 0))
        else:
            sock.bind(('0.0.0.0', 0))
        
        sock.setblocking(False)
        self.local_port = sock.getsockname()[1]
        return sock
    
    def _create_punch_packet(self, packet_type: int) -> bytes:
        """Create encrypted punch packet."""
        # Format: [packet_type:1][nonce:16][encrypted_data]
        nonce = secrets.token_bytes(16)
        data = struct.pack('B', packet_type)
        
        encrypted = self.crypto.encrypt_packet(data)
        return nonce + encrypted
    
    def _parse_packet(self, data: bytes) -> Optional[int]:
        """Parse and decrypt incoming packet."""
        try:
            if len(data) < 17:  # nonce + at least 1 byte
                return None
            
            nonce = data[:16]
            encrypted = data[16:]
            
            # Decrypt
            plaintext = self.crypto.decrypt_packet(encrypted)
            
            if len(plaintext) < 1:
                return None
            
            return struct.unpack('B', plaintext[:1])[0]
            
        except Exception:
            return None
    
    def punch(
        self,
        target_ip: str,
        target_port: int,
        local_port: Optional[int] = None
    ) -> HolePunchResult:
        """
        Attempt to punch a hole through NAT to target.
        
        Args:
            target_ip: Target public IP
            target_port: Target UDP port
            local_port: Optional preferred local port
            
        Returns:
            HolePunchResult with socket if successful
        """
        self._set_state(HolePunchState.PREPARING)
        
        # Create socket
        self.socket = self._create_socket(local_port)
        target_addr = (target_ip, target_port)
        
        self._set_state(HolePunchState.PUNCHING)
        
        start_time = time.time()
        attempts = 0
        last_send_time = 0
        
        while time.time() - start_time < self.timeout:
            attempts += 1
            now = time.time()
            elapsed = now - start_time
            
            # Send punch packet
            if now - last_send_time >= self.retry_interval:
                try:
                    packet = self._create_punch_packet(self.PKT_PUNCH)
                    self.socket.sendto(packet, target_addr)
                    last_send_time = now
                    print(f"[HolePunch] Punch attempt {attempts} to {target_ip}:{target_port}")
                except Exception as e:
                    print(f"[HolePunch] Send error: {e}")
            
            # Try to receive
            try:
                data, addr = self.socket.recvfrom(2048)
                packet_type = self._parse_packet(data)
                
                if packet_type == self.PKT_PUNCH_ACK:
                    latency = (time.time() - start_time) * 1000
                    self._set_state(HolePunchState.CONNECTED)
                    print(f"[HolePunch] Success! Connected to {addr}")
                    print(f"[HolePunch] Latency: {latency:.1f}ms")
                    
                    return HolePunchResult(
                        success=True,
                        socket=self.socket,
                        peer_address=addr,
                        latency_ms=latency,
                        attempts=attempts
                    )
                    
                elif packet_type == self.PKT_PUNCH:
                    # Received punch from peer, send ACK
                    ack_packet = self._create_punch_packet(self.PKT_PUNCH_ACK)
                    self.socket.sendto(ack_packet, addr)
                    print(f"[HolePunch] Received punch from {addr}, sending ACK")
                    
            except BlockingIOError:
                # No data available
                pass
            except Exception as e:
                print(f"[HolePunch] Receive error: {e}")
            
            # Small delay to prevent busy-waiting
            time.sleep(0.01)
        
        # Timeout
        self._set_state(HolePunchState.FAILED)
        self.socket.close()
        self.socket = None
        
        return HolePunchResult(
            success=False,
            socket=None,
            peer_address=None,
            latency_ms=0,
            attempts=attempts,
            error_message="Timeout"
        )
    
    def listen_for_punch(
        self,
        local_port: int,
        expected_ip: Optional[str] = None,
        timeout: float = 60.0
    ) -> HolePunchResult:
        """
        Listen for incoming punch attempts.
        
        Args:
            local_port: Port to listen on
            expected_ip: Optional expected peer IP
            timeout: Listen timeout
            
        Returns:
            HolePunchResult with socket if successful
        """
        self._set_state(HolePunchState.PREPARING)
        
        self.socket = self._create_socket(local_port)
        self.socket.settimeout(1.0)  # 1 second timeout for recv
        
        self._set_state(HolePunchState.PUNCHING)
        
        start_time = time.time()
        attempts = 0
        
        while time.time() - start_time < timeout:
            attempts += 1
            
            try:
                data, addr = self.socket.recvfrom(2048)
                
                # Check if from expected IP
                if expected_ip and addr[0] != expected_ip:
                    print(f"[HolePunch] Ignoring packet from unexpected source: {addr}")
                    continue
                
                packet_type = self._parse_packet(data)
                
                if packet_type == self.PKT_PUNCH:
                    # Send ACK
                    ack_packet = self._create_punch_packet(self.PKT_PUNCH_ACK)
                    self.socket.sendto(ack_packet, addr)
                    
                    latency = (time.time() - start_time) * 1000
                    self._set_state(HolePunchState.CONNECTED)
                    print(f"[HolePunch] Received punch from {addr}, connection established")
                    
                    # Set back to non-blocking for normal operation
                    self.socket.setblocking(False)
                    
                    return HolePunchResult(
                        success=True,
                        socket=self.socket,
                        peer_address=addr,
                        latency_ms=latency,
                        attempts=attempts
                    )
                    
            except socket.timeout:
                continue
            except Exception as e:
                print(f"[HolePunch] Listen error: {e}")
        
        # Timeout
        self._set_state(HolePunchState.FAILED)
        self.socket.close()
        self.socket = None
        
        return HolePunchResult(
            success=False,
            socket=None,
            peer_address=None,
            latency_ms=0,
            attempts=attempts,
            error_message="Listen timeout"
        )
    
    def close(self):
        """Close socket and cleanup."""
        if self.socket:
            self.socket.close()
            self.socket = None
        self._set_state(HolePunchState.IDLE)


# Example usage
if __name__ == "__main__":
    import secrets
    from ..security.encryption import derive_session_keys
    
    # Test setup
    shared_secret = secrets.token_bytes(32)
    keys = derive_session_keys(shared_secret, "test-conn", int(time.time()))
    
    crypto = CryptoManager()
    crypto.set_session_keys(keys)
    
    # This is just for demonstration - real usage requires two endpoints
    print("UDP Hole Punching Module")
    print("=" * 50)
    print("This module provides hole punching capability.")
    print("Use run_server.py or run_client.py for actual connections.")
