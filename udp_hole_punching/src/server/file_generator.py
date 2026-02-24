"""
Security file generator for ClawChat server.

Creates encrypted security files for clients with auto-regeneration.
"""

import os
import time
import secrets
import threading
from typing import Optional
from pathlib import Path

try:
    from ..security.file_manager import SecurityFileManager
except ImportError:
    from security.file_manager import SecurityFileManager


class SecurityFileGenerator:
    """
    Generates security files for initial client connections.
    
    Server-side only. Auto-regenerates files every 10 minutes if no client connected.
    
    Attributes:
        validity_minutes: How long each security file is valid (default: 11 minutes)
        regenerate_interval: How often to regenerate if no client (default: 10 minutes)
    """
    
    VALIDITY_MINUTES = 11  # Session key valid for 11 minutes
    REGENERATE_INTERVAL = 600  # 10 minutes in seconds
    
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
        
        # Auto-regeneration state
        self._last_file_time: float = 0
        self._client_connected: bool = False
        self._regeneration_thread: Optional[threading.Thread] = None
        self._running: bool = False
    
    def set_server_info(self, ip: str, port: int):
        """Set current server IP and port."""
        self._server_ip = ip
        self._current_port = port
    
    def generate_file(self, validity_minutes: int = None) -> str:
        """
        Generate a new security file.
        
        Args:
            validity_minutes: How long the file is valid (default: 11 minutes)
            
        Returns:
            Path to generated file
        """
        if not hasattr(self, '_server_ip') or not self._current_port:
            raise RuntimeError("Server info not set. Call set_server_info() first.")
        
        if validity_minutes is None:
            validity_minutes = self.VALIDITY_MINUTES
        
        # Generate new shared secret
        self._current_secret = secrets.token_bytes(32)
        
        # Create file
        filepath = self.manager.create_security_file(
            server_id=self.server_id,
            server_name=self.server_name,
            server_ip=self._server_ip,
            server_port=self._current_port,
            shared_secret=self._current_secret,
            validity_minutes=validity_minutes
        )
        
        self._last_file_time = time.time()
        print(f"[FileGenerator] Created: {filepath} (valid for {validity_minutes} minutes)")
        return filepath
    
    def mark_client_connected(self):
        """
        Mark that a client has connected.
        Stops auto-regeneration.
        """
        if not self._client_connected:
            self._client_connected = True
            print("[FileGenerator] Client connected - auto-regeneration stopped")
    
    def is_client_connected(self) -> bool:
        """Check if a client has connected."""
        return self._client_connected
    
    def start_auto_regeneration(self):
        """
        Start auto-regeneration thread.
        Regenerates security file every 10 minutes if no client connected.
        """
        if self._regeneration_thread and self._regeneration_thread.is_alive():
            return
        
        self._running = True
        self._regeneration_thread = threading.Thread(target=self._regeneration_loop, daemon=True)
        self._regeneration_thread.start()
        print(f"[FileGenerator] Auto-regeneration started ({self.REGENERATE_INTERVAL}s interval)")
    
    def stop_auto_regeneration(self):
        """Stop auto-regeneration thread."""
        self._running = False
        if self._regeneration_thread:
            self._regeneration_thread.join(timeout=1.0)
    
    def _regeneration_loop(self):
        """Background thread: regenerate file every 10 min if no client."""
        while self._running:
            time.sleep(5)  # Check every 5 seconds
            
            if self._client_connected:
                continue
            
            elapsed = time.time() - self._last_file_time
            if elapsed >= self.REGENERATE_INTERVAL:
                print(f"[FileGenerator] Auto-regenerating (no client for {int(elapsed)}s)")
                try:
                    self.generate_file()
                except Exception as e:
                    print(f"[FileGenerator] Auto-regeneration failed: {e}")
    
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
