"""
Security file manager for ClawChat.

Handles creation, reading, and validation of security files.
Security files are stored in /home/openclaw/clawchat/security/ on server
and loaded via file browser on client.
"""

import os
import json
import time
import glob
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict
from pathlib import Path

from .encryption import CryptoManager


@dataclass
class SecurityFile:
    """Represents a security file's contents."""
    version: str
    protocol: str
    server_id: str
    server_name: str
    server_public_ip: str
    server_udp_port: int
    shared_secret: str  # base64 encoded
    bootstrap_key_id: str
    timestamp: int
    valid_from: int
    valid_until: int
    next_rotation: int
    grace_period: int
    supported_ciphers: List[str]
    nat_traversal: Dict
    compromised_protocol: Dict
    connection_id: str = ""  # Unique connection identifier
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(asdict(self), indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'SecurityFile':
        """Create from JSON string."""
        data = json.loads(json_str)
        return cls(**data)
    
    def is_valid(self) -> bool:
        """Check if the security file is still valid."""
        now = int(time.time())
        return self.valid_from <= now < self.valid_until
    
    def time_until_expiry(self) -> int:
        """Get seconds until expiry."""
        return max(0, self.valid_until - int(time.time()))


class SecurityFileManager:
    """
    Manages security files for server and client.
    
    Server: Creates and stores files in security_directory
    Client: Loads files via file browser
    """
    
    def __init__(self, security_directory: str = None, bootstrap_key: bytes = None):
        """
        Initialize the file manager.
        
        Args:
            security_directory: Directory for security files (server-side)
            bootstrap_key: Key for encrypting/decrypting files
        """
        self.security_directory = security_directory
        self.bootstrap_key = bootstrap_key
        self.crypto = CryptoManager()
        
        if security_directory:
            self._ensure_directory()
    
    def _ensure_directory(self):
        """Create security directory with proper permissions."""
        path = Path(self.security_directory)
        path.mkdir(parents=True, exist_ok=True)
        # Set permissions to 700 (owner only)
        os.chmod(path, 0o700)
    
    def create_security_file(
        self,
        server_id: str,
        server_name: str,
        server_ip: str,
        server_port: int,
        shared_secret: bytes,
        validity_minutes: int = 11,
        connection_id: str = None
    ) -> str:
        """
        Create a new security file (server-side).
        
        Args:
            server_id: Unique server identifier
            server_name: Human-readable server name
            server_ip: Server public IP address
            server_port: Server UDP port
            shared_secret: 32-byte shared secret
            validity_minutes: How long the file is valid (default 11 minutes)
            
        Returns:
            Path to created file
        """
        if not self.security_directory:
            raise RuntimeError("Security directory not configured")
        
        if not self.bootstrap_key:
            raise RuntimeError("Bootstrap key not configured")
        
        now = int(time.time())
        valid_until = now + (validity_minutes * 60)
        next_rotation = now + 600  # 10 minutes
        
        # Generate connection ID if not provided
        if connection_id is None:
            import secrets
            connection_id = f"clawchat-{now}-{secrets.token_hex(8)}"
        
        import base64
        
        security_data = SecurityFile(
            version="2.0",
            protocol="clawchat-file-v2",
            server_id=server_id,
            server_name=server_name,
            server_public_ip=server_ip,
            server_udp_port=server_port,
            shared_secret=base64.b64encode(shared_secret).decode('ascii'),
            bootstrap_key_id="bootstrap-001",
            timestamp=now,
            valid_from=now,
            valid_until=valid_until,
            next_rotation=next_rotation,
            grace_period=300,
            supported_ciphers=["AES-256-GCM"],
            nat_traversal={
                "stun_servers": ["stun.l.google.com:19302"],
                "hole_punch_timeout": 60
            },
            compromised_protocol={
                "signal": "CLAWCHAT_COMPROMISED_V2",
                "response_timeout": 10
            },
            connection_id=connection_id
        )
        
        # Encrypt the data
        plaintext = security_data.to_json().encode('utf-8')
        encrypted = self.crypto.encrypt_file(plaintext, self.bootstrap_key)
        
        # Create filename with timestamp
        timestamp_str = datetime.now().strftime("%Y%m%d-%H%M%S")
        filename = f"clawchat-{timestamp_str}.sec"
        filepath = os.path.join(self.security_directory, filename)
        
        # Write file with restricted permissions
        with open(filepath, 'w') as f:
            json.dump(encrypted, f, indent=2)
        
        os.chmod(filepath, 0o600)  # Owner read/write only
        
        return filepath
    
    def load_security_file(self, filepath: str) -> SecurityFile:
        """
        Load and decrypt a security file (client-side).
        
        Args:
            filepath: Path to security file
            
        Returns:
            SecurityFile object
        """
        if not self.bootstrap_key:
            raise RuntimeError("Bootstrap key not configured")
        
        with open(filepath, 'r') as f:
            encrypted = json.load(f)
        
        # Decrypt
        plaintext = self.crypto.decrypt_file(encrypted, self.bootstrap_key)
        
        # Parse
        return SecurityFile.from_json(plaintext.decode('utf-8'))
    
    def list_security_files(self) -> List[str]:
        """
        List all security files in the directory (server-side).
        
        Returns:
            List of file paths
        """
        if not self.security_directory:
            raise RuntimeError("Security directory not configured")
        
        pattern = os.path.join(self.security_directory, "clawchat-*.sec")
        return sorted(glob.glob(pattern))
    
    def get_latest_security_file(self) -> Optional[str]:
        """
        Get the most recent security file (server-side).
        
        Returns:
            Path to latest file, or None if no files exist
        """
        files = self.list_security_files()
        return files[-1] if files else None
    
    def cleanup_expired_files(self, max_age_hours: int = 24):
        """
        Remove expired security files (server-side).
        
        Args:
            max_age_hours: Remove files older than this many hours
        """
        if not self.security_directory:
            return
        
        cutoff = time.time() - (max_age_hours * 3600)
        
        for filepath in self.list_security_files():
            try:
                mtime = os.path.getmtime(filepath)
                if mtime < cutoff:
                    os.remove(filepath)
                    print(f"Removed expired security file: {filepath}")
            except Exception as e:
                print(f"Error removing {filepath}: {e}")
    
    def validate_security_file(self, filepath: str) -> bool:
        """
        Validate a security file without fully loading it.
        
        Args:
            filepath: Path to security file
            
        Returns:
            True if valid, False otherwise
        """
        try:
            security_file = self.load_security_file(filepath)
            return security_file.is_valid()
        except Exception:
            return False


# Example usage
if __name__ == "__main__":
    import tempfile
    import secrets
    
    # Create temporary directory for testing
    with tempfile.TemporaryDirectory() as tmpdir:
        bootstrap_key = b"test-bootstrap-key-32bytes-long!"
        
        # Server-side: Create file
        server_manager = SecurityFileManager(tmpdir, bootstrap_key)
        
        shared_secret = secrets.token_bytes(32)
        filepath = server_manager.create_security_file(
            server_id="test-server-001",
            server_name="Test Server",
            server_ip="127.0.0.1",
            server_port=54321,
            shared_secret=shared_secret,
            validity_minutes=11
        )
        print(f"Created: {filepath}")
        
        # Client-side: Load file
        client_manager = SecurityFileManager(bootstrap_key=bootstrap_key)
        security_file = client_manager.load_security_file(filepath)
        
        print(f"Server IP: {security_file.server_public_ip}")
        print(f"Server Port: {security_file.server_udp_port}")
        print(f"Valid: {security_file.is_valid()}")
        print(f"Time until expiry: {security_file.time_until_expiry()}s")
