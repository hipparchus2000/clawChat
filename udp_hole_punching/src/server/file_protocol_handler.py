#!/usr/bin/env python3
"""
File Protocol Handler for ClawChat Server

Handles file operations via encrypted UDP protocol.
Integrates with the file_api module from backend-archive.
"""

import os
import base64
import hashlib
from pathlib import Path
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass
from datetime import datetime


@dataclass
class FileInfo:
    """File or directory information."""
    name: str
    path: str
    size: int
    modified: float
    is_dir: bool
    permissions: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'path': self.path,
            'size': self.size,
            'modified': self.modified,
            'is_dir': self.is_dir,
            'permissions': self.permissions
        }


class FileProtocolHandler:
    """
    Handles file protocol messages from clients.
    
    Provides secure file operations with:
    - Path validation (prevents directory traversal)
    - Permission checks
    - Chunked transfers for large files
    """
    
    def __init__(self, base_path: str, allow_write: bool = True):
        """
        Initialize handler.
        
        Args:
            base_path: Root directory for file operations (sandbox)
            allow_write: Whether to allow write operations
        """
        self.base_path = Path(base_path).resolve()
        self.allow_write = allow_write
        self.chunk_size = 8192  # 8KB chunks for transfers
        
        # Ensure base path exists
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def _validate_path(self, relative_path: str) -> Optional[Path]:
        """
        Validate and resolve path.
        
        Args:
            relative_path: Path relative to base_path
            
        Returns:
            Resolved path or None if invalid
        """
        try:
            # Clean the path
            clean_path = relative_path.strip('/').strip('\\')
            if not clean_path:
                clean_path = '.'
            
            # Resolve to absolute
            target = (self.base_path / clean_path).resolve()
            
            # Check it's within base_path (prevent traversal)
            try:
                target.relative_to(self.base_path)
            except ValueError:
                return None
            
            return target
            
        except Exception as e:
            print(f"[FileProtocol] Path validation error: {e}")
            return None
    
    def _get_file_info(self, filepath: Path) -> FileInfo:
        """Get FileInfo for a path."""
        stat = filepath.stat()
        
        # Get relative path
        try:
            rel_path = str(filepath.relative_to(self.base_path))
        except ValueError:
            rel_path = str(filepath)
        
        # Format permissions
        perms = ""
        if filepath.is_dir():
            perms = "drwxr-xr-x"
        else:
            perms = "-rw-r--r--"
        
        return FileInfo(
            name=filepath.name,
            path=rel_path,
            size=stat.st_size if filepath.is_file() else 0,
            modified=stat.st_mtime,
            is_dir=filepath.is_dir(),
            permissions=perms
        )
    
    # ============== Protocol Handlers ==============
    
    def handle_list(self, path: str = ".") -> Dict[str, Any]:
        """
        List directory contents.
        
        Args:
            path: Directory path (relative to base)
            
        Returns:
            Response dict with file list
        """
        target = self._validate_path(path)
        if target is None:
            return {'error': 'Invalid path', 'code': 'INVALID_PATH'}
        
        if not target.exists():
            return {'error': 'Path not found', 'code': 'NOT_FOUND'}
        
        if not target.is_dir():
            return {'error': 'Not a directory', 'code': 'NOT_DIRECTORY'}
        
        try:
            items = []
            for entry in target.iterdir():
                try:
                    info = self._get_file_info(entry)
                    items.append(info.to_dict())
                except Exception as e:
                    print(f"[FileProtocol] Error reading {entry}: {e}")
            
            # Sort: directories first, then alphabetically
            items.sort(key=lambda x: (not x['is_dir'], x['name'].lower()))
            
            return {
                'success': True,
                'path': path,
                'items': items,
                'count': len(items)
            }
            
        except Exception as e:
            return {'error': f'List failed: {e}', 'code': 'LIST_ERROR'}
    
    def handle_download(self, path: str, offset: int = 0, chunk_size: int = None) -> Dict[str, Any]:
        """
        Download file chunk.
        
        Args:
            path: File path
            offset: Byte offset to start from
            chunk_size: Size of chunk (default: self.chunk_size)
            
        Returns:
            Response with file data (base64 encoded)
        """
        if chunk_size is None:
            chunk_size = self.chunk_size
        
        target = self._validate_path(path)
        if target is None:
            return {'error': 'Invalid path', 'code': 'INVALID_PATH'}
        
        if not target.exists():
            return {'error': 'File not found', 'code': 'NOT_FOUND'}
        
        if target.is_dir():
            return {'error': 'Is a directory', 'code': 'IS_DIRECTORY'}
        
        try:
            file_size = target.stat().st_size
            
            with open(target, 'rb') as f:
                f.seek(offset)
                data = f.read(chunk_size)
            
            is_eof = (offset + len(data)) >= file_size
            
            return {
                'success': True,
                'path': path,
                'data': base64.b64encode(data).decode('ascii'),
                'offset': offset,
                'size': len(data),
                'total_size': file_size,
                'eof': is_eof,
                'hash': hashlib.sha256(data).hexdigest()[:16]
            }
            
        except Exception as e:
            return {'error': f'Download failed: {e}', 'code': 'DOWNLOAD_ERROR'}
    
    def handle_upload(self, path: str, data: str, offset: int = 0, append: bool = False) -> Dict[str, Any]:
        """
        Upload file chunk.
        
        Args:
            path: File path
            data: Base64 encoded data
            offset: Byte offset (for resume)
            append: Whether to append to existing file
            
        Returns:
            Response with upload status
        """
        if not self.allow_write:
            return {'error': 'Write operations disabled', 'code': 'WRITE_DISABLED'}
        
        target = self._validate_path(path)
        if target is None:
            return {'error': 'Invalid path', 'code': 'INVALID_PATH'}
        
        # Ensure parent directory exists
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            return {'error': f'Cannot create directory: {e}', 'code': 'MKDIR_ERROR'}
        
        try:
            decoded = base64.b64decode(data)
            
            mode = 'ab' if append else 'wb'
            with open(target, mode) as f:
                if not append and offset > 0:
                    f.seek(offset)
                f.write(decoded)
            
            return {
                'success': True,
                'path': path,
                'bytes_written': len(decoded),
                'offset': offset
            }
            
        except Exception as e:
            return {'error': f'Upload failed: {e}', 'code': 'UPLOAD_ERROR'}
    
    def handle_delete(self, path: str) -> Dict[str, Any]:
        """
        Delete file or directory.
        
        Args:
            path: Path to delete
            
        Returns:
            Response with deletion status
        """
        if not self.allow_write:
            return {'error': 'Write operations disabled', 'code': 'WRITE_DISABLED'}
        
        target = self._validate_path(path)
        if target is None:
            return {'error': 'Invalid path', 'code': 'INVALID_PATH'}
        
        if not target.exists():
            return {'error': 'Path not found', 'code': 'NOT_FOUND'}
        
        try:
            if target.is_dir():
                # Only delete empty directories
                if any(target.iterdir()):
                    return {'error': 'Directory not empty', 'code': 'NOT_EMPTY'}
                target.rmdir()
            else:
                target.unlink()
            
            return {
                'success': True,
                'path': path,
                'message': 'Deleted successfully'
            }
            
        except Exception as e:
            return {'error': f'Delete failed: {e}', 'code': 'DELETE_ERROR'}
    
    def handle_rename(self, path: str, new_name: str) -> Dict[str, Any]:
        """
        Rename file or directory.
        
        Args:
            path: Current path
            new_name: New name (not full path)
            
        Returns:
            Response with rename status
        """
        if not self.allow_write:
            return {'error': 'Write operations disabled', 'code': 'WRITE_DISABLED'}
        
        target = self._validate_path(path)
        if target is None:
            return {'error': 'Invalid path', 'code': 'INVALID_PATH'}
        
        if not target.exists():
            return {'error': 'Path not found', 'code': 'NOT_FOUND'}
        
        # Validate new name (prevent path traversal in new name)
        if '/' in new_name or '\\' in new_name or '..' in new_name:
            return {'error': 'Invalid new name', 'code': 'INVALID_NAME'}
        
        try:
            new_path = target.parent / new_name
            target.rename(new_path)
            
            return {
                'success': True,
                'old_path': path,
                'new_path': str(new_path.relative_to(self.base_path)),
                'message': 'Renamed successfully'
            }
            
        except Exception as e:
            return {'error': f'Rename failed: {e}', 'code': 'RENAME_ERROR'}
    
    def handle_mkdir(self, path: str) -> Dict[str, Any]:
        """
        Create directory.
        
        Args:
            path: Directory path to create
            
        Returns:
            Response with mkdir status
        """
        if not self.allow_write:
            return {'error': 'Write operations disabled', 'code': 'WRITE_DISABLED'}
        
        target = self._validate_path(path)
        if target is None:
            return {'error': 'Invalid path', 'code': 'INVALID_PATH'}
        
        if target.exists():
            return {'error': 'Already exists', 'code': 'ALREADY_EXISTS'}
        
        try:
            target.mkdir(parents=True)
            
            return {
                'success': True,
                'path': path,
                'message': 'Directory created'
            }
            
        except Exception as e:
            return {'error': f'Mkdir failed: {e}', 'code': 'MKDIR_ERROR'}
    
    def handle_stat(self, path: str) -> Dict[str, Any]:
        """
        Get file/directory info.
        
        Args:
            path: Path to stat
            
        Returns:
            Response with file info
        """
        target = self._validate_path(path)
        if target is None:
            return {'error': 'Invalid path', 'code': 'INVALID_PATH'}
        
        if not target.exists():
            return {'error': 'Path not found', 'code': 'NOT_FOUND'}
        
        try:
            info = self._get_file_info(target)
            
            return {
                'success': True,
                'info': info.to_dict()
            }
            
        except Exception as e:
            return {'error': f'Stat failed: {e}', 'code': 'STAT_ERROR'}


# Example usage
if __name__ == '__main__':
    import sys
    import tempfile
    
    # Create temp directory for testing
    with tempfile.TemporaryDirectory() as tmpdir:
        handler = FileProtocolHandler(tmpdir, allow_write=True)
        
        # Create test file
        test_file = Path(tmpdir) / "test.txt"
        test_file.write_text("Hello, World!")
        
        print("Testing File Protocol Handler")
        print("="*50)
        
        # Test list
        print("\n[1] List directory:")
        result = handler.handle_list(".")
        print(f"  Files: {result.get('count', 0)}")
        for item in result.get('items', []):
            print(f"    {item['name']} ({'dir' if item['is_dir'] else 'file'})")
        
        # Test download
        print("\n[2] Download file:")
        result = handler.handle_download("test.txt")
        print(f"  Success: {result.get('success')}")
        print(f"  Size: {result.get('total_size')} bytes")
        
        # Test stat
        print("\n[3] File stat:")
        result = handler.handle_stat("test.txt")
        print(f"  Info: {result.get('info', {})}")
        
        # Test rename
        print("\n[4] Rename file:")
        result = handler.handle_rename("test.txt", "renamed.txt")
        print(f"  Success: {result.get('success')}")
        
        # Test delete
        print("\n[5] Delete file:")
        result = handler.handle_delete("renamed.txt")
        print(f"  Success: {result.get('success')}")
        
        print("\n" + "="*50)
        print("All tests completed!")
