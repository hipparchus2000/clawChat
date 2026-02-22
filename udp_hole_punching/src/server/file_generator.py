"""
Security file generator for ClawChat server.

Creates encrypted security files for clients.
"""

import os
import time
import secrets
from typing import Optional
from pathlib import Path

from ..security.file_manager import SecurityFileManager


class SecurityFileGenerator:
    """
    Generates security files for initial client connections.
    
    Server-side only.
    """
    
    def __init__(
        self,
        security_directory: str,
        bootstrap_key: bytes,
        server_id: str = "clawchat-server",
        server_name: str = "ClawChat Server"
    ):
        """
        Initialize generator.
        
        Args:
            security_directory: Where to store security files
            bootstrap_key: Key for encrypting files
            server_id: Unique server identifier
            server_name: Human-readable name
        """
        self.manager = SecurityFileManager(security_directory, bootstrap_key)
        self.server_id = server_id
        self.server_name = server_name
        self._current_port: Optional[int] = None
        self._current_secret: Optional[bytes] = None
    
    def set_server_info(self, ip: str, port: int):
        """Set current server IP and port."""
        self._server_ip = ip
        self._current_port = port
    
    def generate_file(self, validity_hours: int = 1) -> str:
        """
        Generate a new security file.
        
        Args:
            validity_hours: How long the file is valid
            
        Returns:
            Path to generated file
        """
        if not hasattr(self, '_server_ip') or not self._current_port:
            raise RuntimeError("Server info not set. Call set_server_info() first.")
        
        # Generate new shared secret
        self._current_secret = secrets.token_bytes(32)
        
        # Create file
        filepath = self.manager.create_security_file(
            server_id=self.server_id,
            server_name=self.server_name,
            server_ip=self._server_ip,
            server_port=self._current_port,
            shared_secret=self._current_secret,
            validity_hours=validity_hours
        )
        
        print(f"[FileGenerator] Created: {filepath}")
        return filepath
    
    def get_current_secret(self) -> Optional[bytes]:
        """Get the current shared secret."""
        return self._current_secret
    
    def cleanup_old_files(self, max_age_hours: int = 24):
        """Remove expired security files."""
        self.manager.cleanup_expired_files(max_age_hours)
    
    def list_files(self) -> list:
        """List all security files."""
        return self.manager.list_security_files()


# Example usage
if __name__ == "__main__":
    import tempfile
    
    with tempfile.TemporaryDirectory() as tmpdir:
        bootstrap_key = b"test-bootstrap-key-32bytes-long!"
        
        generator = SecurityFileGenerator(
            tmpdir,
            bootstrap_key,
            server_id="test-server",
            server_name="Test Server"
        )
        
        generator.set_server_info("192.168.1.100", 54321)
        
        filepath = generator.generate_file()
        print(f"Generated: {filepath}")
        
        print(f"Files: {generator.list_files()}")
