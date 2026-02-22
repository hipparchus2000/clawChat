"""
NAT type detection for ClawChat.

Detects NAT type to determine hole punching strategy.
"""

import enum
import socket
from typing import Optional, Tuple
from .stun_client import STUNClient


class NATType(enum.Enum):
    """NAT type enumeration."""
    UNKNOWN = "unknown"
    OPEN = "open"  # No NAT, public IP
    FULL_CONE = "full_cone"  # Accepts any connection
    RESTRICTED_CONE = "restricted_cone"  # Accepts from contacted IPs
    PORT_RESTRICTED = "port_restricted"  # Accepts from contacted IP:port
    SYMMETRIC = "symmetric"  # Different mapping for each destination
    BLOCKED = "blocked"  # STUN failed


class NATDetector:
    """
    Detects NAT type using STUN.
    
    Based on RFC 5780 NAT Behavior Discovery.
    """
    
    def __init__(self, timeout: float = 5.0):
        """
        Initialize NAT detector.
        
        Args:
            timeout: STUN timeout in seconds
        """
        self.timeout = timeout
        self.stun_client = STUNClient(timeout=timeout)
    
    def detect(self) -> NATType:
        """
        Detect NAT type.
        
        Returns:
            NATType enum value
        """
        # Test 1: Get public address
        public_addr = self.stun_client.get_public_address()
        
        if not public_addr:
            return NATType.BLOCKED
        
        public_ip, public_port = public_addr
        
        # Test 2: Check if we have a public IP directly
        local_addrs = self._get_local_addresses()
        if public_ip in local_addrs:
            return NATType.OPEN
        
        # Test 3: Check mapping consistency
        # (Simplified - full test requires multiple STUN servers)
        consistency = self._check_mapping_consistency()
        
        if consistency == "symmetric":
            return NATType.SYMMETRIC
        
        # For cone types, we'd need to test filtering behavior
        # This requires more complex STUN testing
        # For now, assume restricted cone as safe default
        
        return NATType.RESTRICTED_CONE
    
    def _get_local_addresses(self) -> list:
        """Get local IP addresses."""
        addresses = ["127.0.0.1"]
        
        try:
            # Get hostname's IP
            hostname = socket.gethostname()
            host_ip = socket.gethostbyname(hostname)
            addresses.append(host_ip)
            
            # Try to get all interfaces
            import subprocess
            result = subprocess.run(
                ["hostname", "-I"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                for ip in result.stdout.strip().split():
                    if ip not in addresses:
                        addresses.append(ip)
        except Exception:
            pass
        
        return addresses
    
    def _check_mapping_consistency(self) -> str:
        """
        Check if NAT mapping is consistent.
        
        Returns:
            "consistent" or "symmetric"
        """
        # Get mapping from first STUN server
        addr1 = self.stun_client.get_public_address()
        if not addr1:
            return "blocked"
        
        # Create new socket and get mapping again
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(self.timeout)
        
        try:
            addr2 = self.stun_client.get_public_address(sock)
            if not addr2:
                return "unstable"
            
            # Compare
            if addr1[1] == addr2[1]:  # Same port mapping
                return "consistent"
            else:
                return "symmetric"
                
        finally:
            sock.close()
    
    def get_hole_punch_strategy(self, nat_type: NATType) -> dict:
        """
        Get recommended hole punching strategy for NAT type.
        
        Args:
            nat_type: Detected NAT type
            
        Returns:
            Strategy dictionary with recommendations
        """
        strategies = {
            NATType.OPEN: {
                "description": "Direct connection possible",
                "simultaneous": False,
                "timeout": 10,
                "retries": 3,
                "success_rate": 1.0
            },
            NATType.FULL_CONE: {
                "description": "Easy hole punching",
                "simultaneous": True,
                "timeout": 15,
                "retries": 5,
                "success_rate": 0.95
            },
            NATType.RESTRICTED_CONE: {
                "description": "Standard hole punching",
                "simultaneous": True,
                "timeout": 30,
                "retries": 10,
                "success_rate": 0.90
            },
            NATType.PORT_RESTRICTED: {
                "description": "Requires precise timing",
                "simultaneous": True,
                "timeout": 45,
                "retries": 15,
                "success_rate": 0.85
            },
            NATType.SYMMETRIC: {
                "description": "Difficult, may need TURN",
                "simultaneous": True,
                "timeout": 60,
                "retries": 20,
                "success_rate": 0.40,
                "turn_fallback": True
            },
            NATType.BLOCKED: {
                "description": "Connection blocked",
                "simultaneous": False,
                "timeout": 0,
                "retries": 0,
                "success_rate": 0.0
            }
        }
        
        return strategies.get(nat_type, strategies[NATType.UNKNOWN])


# Example usage
if __name__ == "__main__":
    print("Detecting NAT type...")
    
    detector = NATDetector()
    nat_type = detector.detect()
    
    print(f"Detected NAT type: {nat_type.value}")
    
    strategy = detector.get_hole_punch_strategy(nat_type)
    print(f"Strategy: {strategy['description']}")
    print(f"Simultaneous send: {strategy['simultaneous']}")
    print(f"Timeout: {strategy['timeout']}s")
    print(f"Retries: {strategy['retries']}")
    print(f"Expected success rate: {strategy['success_rate']*100:.0f}%")
