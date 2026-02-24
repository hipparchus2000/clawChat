"""
File Protocol Handler for ClawChat Server.

Handles file operations over the encrypted UDP channel.
"""

import os
import json
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class FileInfo:
    """File information."""
    name: str
    path: str
    size: int
    modified: float
    is_dir: bool


class FileProtocolHandler:
    """
    Handles file-related protocol messages.
    
    Provides secure file browsing and transfer capabilities.
    """
    
    def __init__(self, base_path: str = "/home/openclaw"):
        """
        Initialize handler.
        
        Args:
            base_path: Base directory for file operations (sandbox)
        """
        self.base_path = Path(base_path).resolve()
        self.current_path = self.base_path
    
    def validate_path(self, path: str) -> Optional[Path]:
        """
        Validate and sanitize path.
        
        Args:
            path: Requested path
            
        Returns:
            Resolved path or None if invalid
        """
        try:
            # Resolve the path
            requested = Path(path).resolve()
            
            # Ensure it's within base path (prevent directory traversal)
            if not str(requested).startswith(str(self.base_path)):
                return None
            
            return requested
        except Exception:
            return None
    
    def list_directory(self, path: str = None) -> Dict[str, Any]:
        """
        List directory contents.
        
        Args:
            path: Directory path (None for current)
            
        Returns:
            Directory listing response
        """
        if path is None:
            target_path = self.current_path
        else:
            target_path = self.validate_path(path)
            if target_path is None:
                return {'error': 'Invalid path or access denied'}
        
        if not target_path.exists():
            return {'error': 'Path does not exist'}
        
        if not target_path.is_dir():
            return {'error': 'Not a directory'}
        
        try:
            items = []
            
            for entry in os.scandir(target_path):
                stat = entry.stat()
                items.append({
                    'name': entry.name,
                    'path': str(Path(entry.path).relative_to(self.base_path)),
                    'size': stat.st_size if entry.is_file() else 0,
                    'modified': stat.st_mtime,
                    'is_dir': entry.is_dir(),
                    'is_file': entry.is_file()
                })
            
            # Sort: directories first, then files
            items.sort(key=lambda x: (not x['is_dir'], x['name'].lower()))
            
            return {
                'success': True,
                'path': str(target_path.relative_to(self.base_path)),
                'items': items,
                'total': len(items)
            }
            
        except Exception as e:
            return {'error': f'Failed to list directory: {e}'}
    
    def get_file_info(self, path: str) -> Dict[str, Any]:
        """Get file information."""
        target_path = self.validate_path(path)
        if target_path is None:
            return {'error': 'Invalid path or access denied'}
        
        if not target_path.exists():
            return {'error': 'File not found'}
        
        try:
            stat = target_path.stat()
            return {
                'success': True,
                'name': target_path.name,
                'path': str(target_path.relative_to(self.base_path)),
                'size': stat.st_size,
                'modified': stat.st_mtime,
                'is_dir': target_path.is_dir(),
                'is_file': target_path.is_file()
            }
        except Exception as e:
            return {'error': f'Failed to get file info: {e}'}
    
    def read_file_chunk(self, path: str, offset: int = 0, chunk_size: int = 8192) -> Dict[str, Any]:
        """
        Read a chunk of a file.
        
        Args:
            path: File path
            offset: Byte offset
            chunk_size: Bytes to read
            
        Returns:
            File data response
        """
        target_path = self.validate_path(path)
        if target_path is None:
            return {'error': 'Invalid path or access denied'}
        
        if not target_path.exists() or not target_path.is_file():
            return {'error': 'File not found'}
        
        try:
            with open(target_path, 'rb') as f:
                f.seek(offset)
                data = f.read(chunk_size)
            
            import base64
            return {
                'success': True,
                'data': base64.b64encode(data).decode('ascii'),
                'offset': offset,
                'size': len(data),
                'eof': len(data) < chunk_size
            }
        except Exception as e:
            return {'error': f'Failed to read file: {e}'}
    
    def write_file_chunk(self, path: str, data: str, offset: int = 0) -> Dict[str, Any]:
        """
        Write a chunk to a file.
        
        Args:
            path: File path
            data: Base64 encoded data
            offset: Byte offset
            
        Returns:
            Write response
        """
        target_path = self.validate_path(path)
        if target_path is None:
            return {'error': 'Invalid path or access denied'}
        
        try:
            import base64
            decoded = base64.b64decode(data)
            
            mode = 'wb' if offset == 0 else 'r+b'
            with open(target_path, mode) as f:
                if offset > 0:
                    f.seek(offset)
                f.write(decoded)
            
            return {
                'success': True,
                'bytes_written': len(decoded)
            }
        except Exception as e:
            return {'error': f'Failed to write file: {e}'}
    
    def delete_file(self, path: str) -> Dict[str, Any]:
        """Delete a file or directory."""
        target_path = self.validate_path(path)
        if target_path is None:
            return {'error': 'Invalid path or access denied'}
        
        if not target_path.exists():
            return {'error': 'Path not found'}
        
        try:
            if target_path.is_dir():
                os.rmdir(target_path)  # Only empty directories
            else:
                os.remove(target_path)
            
            return {'success': True, 'message': 'Deleted successfully'}
        except Exception as e:
            return {'error': f'Failed to delete: {e}'}
    
    def mkdir(self, path: str) -> Dict[str, Any]:
        """Create a directory."""
        target_path = self.validate_path(path)
        if target_path is None:
            return {'error': 'Invalid path or access denied'}
        
        try:
            os.makedirs(target_path, exist_ok=True)
            return {'success': True, 'message': 'Directory created'}
        except Exception as e:
            return {'error': f'Failed to create directory: {e}'}


class CrontabProtocolHandler:
    """
    Handles crontab-related protocol messages.
    """
    
    def __init__(self):
        self.crontab_file = "/var/spool/cron/crontabs/openclaw"
    
    def list_crontab(self) -> Dict[str, Any]:
        """List all crontab entries."""
        try:
            if not os.path.exists(self.crontab_file):
                return {'success': True, 'entries': []}
            
            entries = []
            with open(self.crontab_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    # Parse crontab line
                    parts = line.split(None, 5)
                    if len(parts) >= 6:
                        schedule = ' '.join(parts[:5])
                        command = parts[5]
                        comment = ""
                        
                        entries.append({
                            'schedule': schedule,
                            'command': command,
                            'comment': comment,
                            'raw': line
                        })
            
            return {'success': True, 'entries': entries}
            
        except Exception as e:
            return {'error': f'Failed to read crontab: {e}'}
    
    def add_entry(self, schedule: str, command: str, comment: str = "") -> Dict[str, Any]:
        """Add crontab entry."""
        try:
            entry = f"{schedule}\t{command}"
            if comment:
                entry += f" # {comment}"
            entry += "\n"
            
            with open(self.crontab_file, 'a') as f:
                f.write(entry)
            
            return {'success': True, 'message': 'Entry added'}
        except Exception as e:
            return {'error': f'Failed to add entry: {e}'}
    
    def remove_entry(self, line_number: int) -> Dict[str, Any]:
        """Remove crontab entry by line number."""
        try:
            with open(self.crontab_file, 'r') as f:
                lines = f.readlines()
            
            # Find non-comment, non-empty lines
            entry_lines = []
            for i, line in enumerate(lines):
                stripped = line.strip()
                if stripped and not stripped.startswith('#'):
                    entry_lines.append(i)
            
            if line_number < 0 or line_number >= len(entry_lines):
                return {'error': 'Invalid line number'}
            
            # Remove the line
            del lines[entry_lines[line_number]]
            
            with open(self.crontab_file, 'w') as f:
                f.writelines(lines)
            
            return {'success': True, 'message': 'Entry removed'}
        except Exception as e:
            return {'error': f'Failed to remove entry: {e}'}
