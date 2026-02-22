"""
STUN client for NAT traversal.

Helps discover public IP and port behind NAT.
"""

import socket
import struct
import random
from typing import Optional, Tuple


class STUNError(Exception):
    """STUN operation error."""
    pass


class STUNClient:
    """
    Simple STUN client for discovering public IP/port.
    
    Uses Google's public STUN servers by default.
    """
    
    # Google STUN servers
    DEFAULT_SERVERS = [
        ("stun.l.google.com", 19302),
        ("stun1.l.google.com", 19302),
        ("stun2.l.google.com", 19302),
        ("stun3.l.google.com", 19302),
        ("stun4.l.google.com", 19302),
    ]
    
    # STUN message types
    BINDING_REQUEST = 0x0001
    BINDING_RESPONSE = 0x0101
    
    # STUN attributes
    MAPPED_ADDRESS = 0x0001
    XOR_MAPPED_ADDRESS = 0x0020
    
    def __init__(self, servers: list = None, timeout: float = 5.0):
        """
        Initialize STUN client.
        
        Args:
            servers: List of (host, port) tuples (defaults to Google servers)
            timeout: Socket timeout in seconds
        """
        self.servers = servers or self.DEFAULT_SERVERS
        self.timeout = timeout
    
    def _create_binding_request(self) -> bytes:
        """Create a STUN binding request."""
        # Message type: Binding Request
        msg_type = struct.pack('>H', self.BINDING_REQUEST)
        
        # Message length (no attributes)
        msg_len = struct.pack('>H', 0)
        
        # Magic cookie
        magic_cookie = struct.pack('>I', 0x2112A442)
        
        # Transaction ID (12 bytes)
        transaction_id = bytes([random.randint(0, 255) for _ in range(12)])
        
        return msg_type + msg_len + magic_cookie + transaction_id
    
    def _parse_address(self, data: bytes, offset: int) -> Tuple[str, int]:
        """Parse address from STUN attribute."""
        # Skip first byte (unused)
        family = data[offset + 1]
        port = struct.unpack('>H', data[offset + 2:offset + 4])[0]
        
        if family == 0x01:  # IPv4
            ip = '.'.join(str(b) for b in data[offset + 4:offset + 8])
        else:  # IPv6
            ip = ':'.join(
                format(struct.unpack('>H', data[i:i+2])[0], '04x')
                for i in range(offset + 4, offset + 20, 2)
            )
        
        return ip, port
    
    def _parse_xor_address(self, data: bytes, offset: int, magic_cookie: bytes) -> Tuple[str, int]:
        """Parse XOR-mapped address."""
        # Port is XORed with first 2 bytes of magic cookie
        xport = struct.unpack('>H', data[offset + 2:offset + 4])[0]
        port = xport ^ struct.unpack('>H', magic_cookie[:2])[0]
        
        # IP is XORed with magic cookie
        family = data[offset + 1]
        
        if family == 0x01:  # IPv4
            ip_bytes = bytearray(4)
            for i in range(4):
                ip_bytes[i] = data[offset + 4 + i] ^ magic_cookie[i]
            ip = '.'.join(str(b) for b in ip_bytes)
        else:  # IPv6
            ip_parts = []
            for i in range(8):
                xpart = struct.unpack('>H', data[offset + 4 + i*2:offset + 6 + i*2])[0]
                if i < 2:
                    part = xpart ^ struct.unpack('>H', magic_cookie[i*2:i*2+2])[0]
                else:
                    part = xpart  # Remaining bytes are XORed with transaction ID
                ip_parts.append(format(part, '04x'))
            ip = ':'.join(ip_parts)
        
        return ip, port
    
    def _parse_response(self, data: bytes) -> Optional[Tuple[str, int]]:
        """Parse STUN binding response."""
        if len(data) < 20:
            return None
        
        msg_type = struct.unpack('>H', data[0:2])[0]
        if msg_type != self.BINDING_RESPONSE:
            return None
        
        magic_cookie = data[4:8]
        
        # Parse attributes
        offset = 20
        while offset < len(data):
            if offset + 4 > len(data):
                break
            
            attr_type = struct.unpack('>H', data[offset:offset + 2])[0]
            attr_len = struct.unpack('>H', data[offset + 2:offset + 4])[0]
            
            if attr_type == self.MAPPED_ADDRESS:
                return self._parse_address(data, offset + 4)
            elif attr_type == self.XOR_MAPPED_ADDRESS:
                return self._parse_xor_address(data, offset + 4, magic_cookie)
            
            # Move to next attribute (with padding)
            offset += 4 + attr_len
            if attr_len % 4 != 0:
                offset += 4 - (attr_len % 4)
        
        return None
    
    def get_public_address(
        self,
        local_socket: Optional[socket.socket] = None
    ) -> Optional[Tuple[str, int]]:
        """
        Discover public IP and port using STUN.
        
        Args:
            local_socket: Optional socket to use (creates new if None)
            
        Returns:
            Tuple of (public_ip, public_port) or None if failed
        """
        sock = local_socket or socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(self.timeout)
        
        try:
            request = self._create_binding_request()
            
            for server_host, server_port in self.servers:
                try:
                    # Send request
                    sock.sendto(request, (server_host, server_port))
                    
                    # Receive response
                    data, addr = sock.recvfrom(1024)
                    
                    # Parse response
                    result = self._parse_response(data)
                    if result:
                        return result
                        
                except socket.timeout:
                    continue
                except Exception as e:
                    print(f"STUN server {server_host} failed: {e}")
                    continue
            
            return None
            
        finally:
            if not local_socket:
                sock.close()
    
    def test_nat_type(self) -> str:
        """
        Basic NAT type detection.
        
        Returns:
            String describing NAT type (simplified)
        """
        # This is a simplified check
        # Full NAT type detection requires multiple STUN servers
        # and complex logic (see RFC 5780)
        
        addr1 = self.get_public_address()
        if not addr1:
            return "blocked"
        
        # Try again
        addr2 = self.get_public_address()
        if not addr2:
            return "unstable"
        
        if addr1 == addr2:
            return "consistent"
        else:
            return "symmetric"


# Example usage
if __name__ == "__main__":
    client = STUNClient()
    
    print("Testing STUN discovery...")
    result = client.get_public_address()
    
    if result:
        ip, port = result
        print(f"Public address: {ip}:{port}")
        
        nat_type = client.test_nat_type()
        print(f"NAT type: {nat_type}")
    else:
        print("Failed to discover public address")
