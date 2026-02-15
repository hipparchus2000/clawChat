"""Mock Mega.nz service for testing ClawChat without real API calls.

This module provides a mock implementation of the Mega.nz API
for use in unit and integration tests. It simulates file upload,
download, and management operations without making actual network calls.
"""

import asyncio
import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, BinaryIO, Dict, List, Optional, Union
from unittest.mock import MagicMock
import io


@dataclass
class MockMegaFile:
    """Represents a file stored in the mock Mega service."""
    name: str
    content: bytes
    file_id: str = field(default_factory=lambda: hashlib.sha256(
        str(time.time()).encode()).hexdigest()[:16])
    size: int = field(init=False)
    created_at: float = field(default_factory=time.time)
    modified_at: float = field(default_factory=time.time)
    parent_id: Optional[str] = None
    
    def __post_init__(self):
        self.size = len(self.content)


@dataclass
class MockMegaFolder:
    """Represents a folder in the mock Mega service."""
    name: str
    folder_id: str = field(default_factory=lambda: hashlib.sha256(
        str(time.time()).encode()).hexdigest()[:16])
    parent_id: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    children: List[str] = field(default_factory=list)


class MockMegaAPI:
    """Mock implementation of Mega.nz API for testing.
    
    This class simulates the Mega.nz API without making actual network calls.
    It stores files and folders in memory and provides similar interface
    to the real Mega API.
    
    Example:
        >>> mega = MockMegaAPI()
        >>> mega.login('test@example.com', 'password123')
        >>> file_id = mega.upload('test.txt', b'Hello World')
        >>> downloaded = mega.download(file_id)
        >>> print(downloaded)  # b'Hello World'
    """
    
    def __init__(self):
        """Initialize the mock Mega API."""
        self._files: Dict[str, MockMegaFile] = {}
        self._folders: Dict[str, MockMegaFolder] = {}
        self._is_logged_in = False
        self._current_user = None
        self._storage_quota = 50 * 1024 * 1024 * 1024  # 50 GB default
        self._storage_used = 0
        self._upload_delay = 0.1  # Simulate network delay
        self._download_delay = 0.05
        self._should_fail_next = False
        self._failure_exception = Exception("Simulated API failure")
        
        # Create root folder
        root = MockMegaFolder(name="Root", folder_id="root")
        self._folders["root"] = root
    
    def login(self, email: str, password: str) -> bool:
        """Simulate login to Mega.nz.
        
        Args:
            email: User email address.
            password: User password.
            
        Returns:
            True if login successful, False otherwise.
        """
        if self._should_fail_next:
            self._should_fail_next = False
            raise self._failure_exception
            
        # Simulate authentication delay
        time.sleep(0.05)
        
        if email and password and len(password) >= 6:
            self._is_logged_in = True
            self._current_user = {
                'email': email,
                'name': email.split('@')[0]
            }
            return True
        return False
    
    def logout(self) -> None:
        """Log out from the mock service."""
        self._is_logged_in = False
        self._current_user = None
    
    def is_logged_in(self) -> bool:
        """Check if user is logged in."""
        return self._is_logged_in
    
    def get_user(self) -> Optional[Dict[str, str]]:
        """Get current user information."""
        return self._current_user.copy() if self._current_user else None
    
    def upload(
        self, 
        filename: str, 
        data: Union[bytes, str, BinaryIO],
        dest_folder: Optional[str] = None
    ) -> str:
        """Upload a file to mock Mega storage.
        
        Args:
            filename: Name of the file.
            data: File content (bytes, string, or file-like object).
            dest_folder: Destination folder ID (default: root).
            
        Returns:
            File ID of the uploaded file.
            
        Raises:
            Exception: If not logged in or upload fails.
        """
        if self._should_fail_next:
            self._should_fail_next = False
            raise self._failure_exception
        
        if not self._is_logged_in:
            raise Exception("Not logged in")
        
        # Convert data to bytes
        if isinstance(data, str):
            content = data.encode('utf-8')
        elif hasattr(data, 'read'):
            content = data.read()
            if isinstance(content, str):
                content = content.encode('utf-8')
        else:
            content = data
        
        # Check storage quota
        if self._storage_used + len(content) > self._storage_quota:
            raise Exception("Storage quota exceeded")
        
        # Simulate upload delay
        time.sleep(self._upload_delay)
        
        parent_id = dest_folder or "root"
        
        # Create file
        file_obj = MockMegaFile(
            name=filename,
            content=content,
            parent_id=parent_id
        )
        
        self._files[file_obj.file_id] = file_obj
        self._storage_used += len(content)
        
        # Add to folder
        if parent_id in self._folders:
            self._folders[parent_id].children.append(file_obj.file_id)
        
        return file_obj.file_id
    
    def upload_json(
        self, 
        filename: str, 
        data: Any,
        dest_folder: Optional[str] = None
    ) -> str:
        """Upload JSON data as a file.
        
        Args:
            filename: Name of the file.
            data: JSON-serializable data.
            dest_folder: Destination folder ID.
            
        Returns:
            File ID of the uploaded file.
        """
        json_data = json.dumps(data, indent=2)
        return self.upload(filename, json_data, dest_folder)
    
    def download(self, file_id: str) -> bytes:
        """Download a file from mock Mega storage.
        
        Args:
            file_id: ID of the file to download.
            
        Returns:
            File content as bytes.
            
        Raises:
            Exception: If file not found or download fails.
        """
        if self._should_fail_next:
            self._should_fail_next = False
            raise self._failure_exception
        
        if not self._is_logged_in:
            raise Exception("Not logged in")
        
        # Simulate download delay
        time.sleep(self._download_delay)
        
        if file_id not in self._files:
            raise Exception(f"File not found: {file_id}")
        
        return self._files[file_id].content
    
    def download_json(self, file_id: str) -> Any:
        """Download and parse a JSON file.
        
        Args:
            file_id: ID of the file to download.
            
        Returns:
            Parsed JSON data.
        """
        content = self.download(file_id)
        return json.loads(content.decode('utf-8'))
    
    def delete(self, file_id: str) -> bool:
        """Delete a file from mock Mega storage.
        
        Args:
            file_id: ID of the file to delete.
            
        Returns:
            True if deleted successfully.
        """
        if self._should_fail_next:
            self._should_fail_next = False
            raise self._failure_exception
        
        if not self._is_logged_in:
            raise Exception("Not logged in")
        
        if file_id not in self._files:
            raise Exception(f"File not found: {file_id}")
        
        file_obj = self._files.pop(file_id)
        self._storage_used -= file_obj.size
        
        # Remove from folder
        if file_obj.parent_id and file_obj.parent_id in self._folders:
            folder = self._folders[file_obj.parent_id]
            if file_id in folder.children:
                folder.children.remove(file_id)
        
        return True
    
    def find(self, pattern: str = None) -> List[Dict[str, Any]]:
        """Find files matching a pattern.
        
        Args:
            pattern: Optional filename pattern to match.
            
        Returns:
            List of file information dictionaries.
        """
        if not self._is_logged_in:
            raise Exception("Not logged in")
        
        results = []
        for file_id, file_obj in self._files.items():
            if pattern is None or pattern in file_obj.name:
                results.append({
                    'file_id': file_id,
                    'name': file_obj.name,
                    'size': file_obj.size,
                    'created_at': file_obj.created_at,
                    'modified_at': file_obj.modified_at
                })
        
        return results
    
    def get_file_info(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific file.
        
        Args:
            file_id: ID of the file.
            
        Returns:
            File information dictionary or None if not found.
        """
        if file_id not in self._files:
            return None
        
        file_obj = self._files[file_id]
        return {
            'file_id': file_obj.file_id,
            'name': file_obj.name,
            'size': file_obj.size,
            'created_at': file_obj.created_at,
            'modified_at': file_obj.modified_at,
            'parent_id': file_obj.parent_id
        }
    
    def create_folder(self, name: str, parent_id: str = "root") -> str:
        """Create a new folder.
        
        Args:
            name: Folder name.
            parent_id: Parent folder ID.
            
        Returns:
            New folder ID.
        """
        if self._should_fail_next:
            self._should_fail_next = False
            raise self._failure_exception
        
        if not self._is_logged_in:
            raise Exception("Not logged in")
        
        folder = MockMegaFolder(name=name, parent_id=parent_id)
        self._folders[folder.folder_id] = folder
        
        if parent_id in self._folders:
            self._folders[parent_id].children.append(folder.folder_id)
        
        return folder.folder_id
    
    def list_folder(self, folder_id: str = "root") -> Dict[str, Any]:
        """List contents of a folder.
        
        Args:
            folder_id: Folder ID to list.
            
        Returns:
            Dictionary with 'files' and 'folders' lists.
        """
        if not self._is_logged_in:
            raise Exception("Not logged in")
        
        if folder_id not in self._folders:
            raise Exception(f"Folder not found: {folder_id}")
        
        folder = self._folders[folder_id]
        files = []
        subfolders = []
        
        for child_id in folder.children:
            if child_id in self._files:
                files.append(self.get_file_info(child_id))
            elif child_id in self._folders:
                f = self._folders[child_id]
                subfolders.append({
                    'folder_id': f.folder_id,
                    'name': f.name,
                    'created_at': f.created_at
                })
        
        return {
            'folder_id': folder_id,
            'name': folder.name,
            'files': files,
            'folders': subfolders
        }
    
    def get_storage_quota(self) -> Dict[str, int]:
        """Get storage quota information.
        
        Returns:
            Dictionary with 'total', 'used', and 'free' bytes.
        """
        return {
            'total': self._storage_quota,
            'used': self._storage_used,
            'free': self._storage_quota - self._storage_used
        }
    
    def set_storage_quota(self, quota_bytes: int) -> None:
        """Set the storage quota (for testing)."""
        self._storage_quota = quota_bytes
    
    def set_fail_next(self, exception: Exception = None) -> None:
        """Make the next API call fail.
        
        This is useful for testing error handling.
        
        Args:
            exception: Exception to raise. Uses default if not provided.
        """
        self._should_fail_next = True
        if exception:
            self._failure_exception = exception
    
    def clear_fail_next(self) -> None:
        """Clear the fail next flag."""
        self._should_fail_next = False
    
    def set_delays(self, upload: float = None, download: float = None) -> None:
        """Set simulated network delays.
        
        Args:
            upload: Upload delay in seconds.
            download: Download delay in seconds.
        """
        if upload is not None:
            self._upload_delay = upload
        if download is not None:
            self._download_delay = download
    
    def reset(self) -> None:
        """Reset the mock API to initial state."""
        self._files.clear()
        self._folders.clear()
        self._is_logged_in = False
        self._current_user = None
        self._storage_used = 0
        self._should_fail_next = False
        
        # Recreate root folder
        root = MockMegaFolder(name="Root", folder_id="root")
        self._folders["root"] = root


class AsyncMockMegaAPI:
    """Async wrapper for MockMegaAPI.
    
    Provides async versions of all methods for use with async test code.
    """
    
    def __init__(self):
        self._sync_api = MockMegaAPI()
    
    async def login(self, email: str, password: str) -> bool:
        """Async login."""
        await asyncio.sleep(0.01)  # Simulate async
        return self._sync_api.login(email, password)
    
    async def logout(self) -> None:
        """Async logout."""
        await asyncio.sleep(0.01)
        self._sync_api.logout()
    
    async def upload(
        self, 
        filename: str, 
        data: Union[bytes, str, BinaryIO],
        dest_folder: Optional[str] = None
    ) -> str:
        """Async upload."""
        await asyncio.sleep(self._sync_api._upload_delay)
        return self._sync_api.upload(filename, data, dest_folder)
    
    async def download(self, file_id: str) -> bytes:
        """Async download."""
        await asyncio.sleep(self._sync_api._download_delay)
        return self._sync_api.download(file_id)
    
    async def delete(self, file_id: str) -> bool:
        """Async delete."""
        await asyncio.sleep(0.01)
        return self._sync_api.delete(file_id)
    
    async def find(self, pattern: str = None) -> List[Dict[str, Any]]:
        """Async find."""
        await asyncio.sleep(0.01)
        return self._sync_api.find(pattern)
    
    async def create_folder(self, name: str, parent_id: str = "root") -> str:
        """Async create folder."""
        await asyncio.sleep(0.01)
        return self._sync_api.create_folder(name, parent_id)
    
    async def list_folder(self, folder_id: str = "root") -> Dict[str, Any]:
        """Async list folder."""
        await asyncio.sleep(0.01)
        return self._sync_api.list_folder(folder_id)
    
    def __getattr__(self, name: str) -> Any:
        """Delegate attribute access to sync API."""
        return getattr(self._sync_api, name)


def create_mock_mega() -> MockMegaAPI:
    """Factory function to create a MockMegaAPI instance.
    
    Returns:
        New MockMegaAPI instance.
    """
    return MockMegaAPI()


def create_async_mock_mega() -> AsyncMockMegaAPI:
    """Factory function to create an AsyncMockMegaAPI instance.
    
    Returns:
        New AsyncMockMegaAPI instance.
    """
    return AsyncMockMegaAPI()
