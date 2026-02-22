"""
ClawChat File System API - Path Validator
=========================================
Provides path validation and directory traversal protection.
"""

import os
import re
from pathlib import Path
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class PathValidationError(Exception):
    """Raised when path validation fails."""
    pass


class DirectoryTraversalError(PathValidationError):
    """Raised when a directory traversal attempt is detected."""
    pass


class InvalidPathError(PathValidationError):
    """Raised when a path is invalid for other reasons."""
    pass


class PathValidator:
    """
    Validates and sanitizes file system paths to prevent directory traversal attacks.
    """
    
    # Patterns that indicate directory traversal attempts
    TRAVERSAL_PATTERNS = [
        r'\.\./',           # ../
        r'\.\.\\',          # ..\ (Windows)
        r'%2e%2e%2f',       # URL encoded ../
        r'%2e%2e/',         # Mixed encoding
        r'\.\.//',          # Double slash
        r'^\.\./',          # Starting with ../
        r'/\.\.$',          # Ending with /..
        r'\\\.\.$',         # Windows ending with \..
    ]
    
    # Suspicious path patterns
    SUSPICIOUS_PATTERNS = [
        r'\0',              # Null bytes
        r'[~\x00-\x1f]',    # Control characters
        r'\.\.$',           # Ending with ..
        r'^\.+$',           # Just dots
    ]
    
    def __init__(
        self,
        root_directory: str,
        allow_hidden: bool = False,
        allowed_extensions: Optional[list] = None,
        max_path_length: int = 4096,
        max_filename_length: int = 255
    ):
        """
        Initialize the path validator.
        
        Args:
            root_directory: The root directory that all paths must be within
            allow_hidden: Whether to allow hidden files/directories (starting with .)
            allowed_extensions: List of allowed file extensions (None = allow all)
            max_path_length: Maximum allowed path length
            max_filename_length: Maximum allowed filename length
        """
        self.root_directory = Path(root_directory).resolve()
        self.allow_hidden = allow_hidden
        self.allowed_extensions = allowed_extensions
        self.max_path_length = max_path_length
        self.max_filename_length = max_filename_length
        
        # Compile traversal detection patterns
        self._traversal_regex = re.compile('|'.join(self.TRAVERSAL_PATTERNS), re.IGNORECASE)
        self._suspicious_regex = re.compile('|'.join(self.SUSPICIOUS_PATTERNS))
        
        logger.info(f"PathValidator initialized with root: {self.root_directory}")
    
    def validate(self, path: str) -> Path:
        """
        Validate a path and return the resolved Path object if valid.
        
        Args:
            path: The path to validate
            
        Returns:
            Resolved Path object
            
        Raises:
            DirectoryTraversalError: If directory traversal is detected
            InvalidPathError: If the path is invalid for other reasons
        """
        if not path:
            raise InvalidPathError("Path cannot be empty")
        
        # Check path length
        if len(path) > self.max_path_length:
            raise InvalidPathError(f"Path exceeds maximum length of {self.max_path_length}")
        
        # Check for null bytes and control characters
        if '\x00' in path:
            raise InvalidPathError("Path contains null bytes")
        
        # Check for directory traversal patterns
        normalized_path = path.replace('\\', '/')
        if self._traversal_regex.search(normalized_path):
            logger.warning(f"Directory traversal attempt detected: {path}")
            raise DirectoryTraversalError("Directory traversal attempt detected")
        
        # Check for suspicious patterns
        if self._suspicious_regex.search(path):
            logger.warning(f"Suspicious path pattern detected: {path}")
            raise InvalidPathError("Suspicious path pattern detected")
        
        # Resolve the path
        try:
            # Start from root directory
            if os.path.isabs(path):
                # Remove leading slash and join with root
                relative_path = path.lstrip('/')
                full_path = self.root_directory / relative_path
            else:
                full_path = self.root_directory / path
            
            # Resolve to absolute path (removes .. and .)
            resolved_path = full_path.resolve()
            
        except (OSError, ValueError) as e:
            raise InvalidPathError(f"Failed to resolve path: {e}")
        
        # Ensure the resolved path is still within root directory
        try:
            resolved_path.relative_to(self.root_directory)
        except ValueError:
            logger.warning(f"Path escapes root directory: {path} -> {resolved_path}")
            raise DirectoryTraversalError("Path escapes allowed directory")
        
        # Check for hidden files
        if not self.allow_hidden:
            parts = resolved_path.relative_to(self.root_directory).parts
            for part in parts:
                if part.startswith('.') and part not in ('.', '..'):
                    logger.warning(f"Hidden file/directory access attempted: {part}")
                    raise InvalidPathError("Hidden files/directories are not allowed")
        
        # Check filename length
        filename = resolved_path.name
        if len(filename) > self.max_filename_length:
            raise InvalidPathError(f"Filename exceeds maximum length of {self.max_filename_length}")
        
        # Check file extension if restricted
        if self.allowed_extensions and resolved_path.is_file():
            ext = resolved_path.suffix.lower()
            if ext not in self.allowed_extensions:
                raise InvalidPathError(f"File extension '{ext}' is not allowed")
        
        return resolved_path
    
    def validate_directory(self, path: str) -> Path:
        """
        Validate a path and ensure it points to a directory.
        
        Args:
            path: The path to validate
            
        Returns:
            Resolved Path object
            
        Raises:
            DirectoryTraversalError: If directory traversal is detected
            InvalidPathError: If the path is invalid or not a directory
        """
        resolved = self.validate(path)
        
        if not resolved.exists():
            raise InvalidPathError(f"Directory not found: {path}")
        
        if not resolved.is_dir():
            raise InvalidPathError(f"Path is not a directory: {path}")
        
        return resolved
    
    def validate_file(self, path: str) -> Path:
        """
        Validate a path and ensure it points to a file.
        
        Args:
            path: The path to validate
            
        Returns:
            Resolved Path object
            
        Raises:
            DirectoryTraversalError: If directory traversal is detected
            InvalidPathError: If the path is invalid or not a file
        """
        resolved = self.validate(path)
        
        if not resolved.exists():
            raise InvalidPathError(f"File not found: {path}")
        
        if not resolved.is_file():
            raise InvalidPathError(f"Path is not a file: {path}")
        
        return resolved
    
    def sanitize_filename(self, filename: str) -> str:
        """
        Sanitize a filename to remove dangerous characters.
        
        Args:
            filename: The filename to sanitize
            
        Returns:
            Sanitized filename
        """
        # Remove path separators
        filename = filename.replace('/', '_').replace('\\', '_')
        
        # Remove null bytes
        filename = filename.replace('\x00', '')
        
        # Remove control characters
        filename = ''.join(char for char in filename if ord(char) >= 32)
        
        # Remove leading/trailing dots and spaces
        filename = filename.strip('. ')
        
        # Ensure filename is not empty
        if not filename:
            filename = 'unnamed'
        
        # Limit length
        if len(filename) > self.max_filename_length:
            name, ext = os.path.splitext(filename)
            filename = name[:self.max_filename_length - len(ext)] + ext
        
        return filename
    
    def get_relative_path(self, full_path: Path) -> str:
        """
        Get the path relative to the root directory.
        
        Args:
            full_path: The full resolved path
            
        Returns:
            Relative path as string
        """
        try:
            return str(full_path.relative_to(self.root_directory))
        except ValueError:
            raise DirectoryTraversalError("Path is outside root directory")
    
    def is_path_within_root(self, path: str) -> bool:
        """
        Check if a path would be within the root directory when resolved.
        
        Args:
            path: The path to check
            
        Returns:
            True if path would be within root, False otherwise
        """
        try:
            self.validate(path)
            return True
        except PathValidationError:
            return False


# Global validator instance (will be configured during API initialization)
_default_validator: Optional[PathValidator] = None


def get_validator() -> PathValidator:
    """Get the default path validator instance."""
    if _default_validator is None:
        raise RuntimeError("Path validator not initialized. Call initialize_validator() first.")
    return _default_validator


def initialize_validator(
    root_directory: str,
    allow_hidden: bool = False,
    allowed_extensions: Optional[list] = None
) -> PathValidator:
    """Initialize the global path validator."""
    global _default_validator
    _default_validator = PathValidator(
        root_directory=root_directory,
        allow_hidden=allow_hidden,
        allowed_extensions=allowed_extensions
    )
    return _default_validator
