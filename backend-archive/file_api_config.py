"""
ClawChat File System API Configuration
======================================
Configuration settings for the file system API.
"""

import os
from typing import List, Optional


class FileAPIConfig:
    """Configuration for the File System API."""
    
    # Root directory for file operations
    ROOT_DIRECTORY: str = "/root/.openclaw/workspace/projects/"
    
    # Allow hidden files (starting with .)
    ALLOW_HIDDEN_FILES: bool = False
    
    # Require authentication for all operations
    REQUIRE_AUTHENTICATION: bool = False
    
    # Secret key for token generation (should be set from environment in production)
    SECRET_KEY: Optional[str] = os.environ.get('FILE_API_SECRET_KEY')
    
    # Allowed CORS origins
    ALLOWED_ORIGINS: List[str] = ["*"]
    
    # Rate limiting settings
    RATE_LIMIT_LIST_MAX: int = 60      # requests per window
    RATE_LIMIT_DOWNLOAD_MAX: int = 30  # requests per window
    RATE_LIMIT_METADATA_MAX: int = 120 # requests per window
    RATE_LIMIT_WINDOW_SECONDS: int = 60
    
    # File transfer settings
    DEFAULT_CHUNK_SIZE: int = 8192      # 8KB chunks for file reading
    MAX_CHUNK_SIZE: int = 65536         # 64KB max chunk size
    MAX_FILE_SIZE: int = 1024 * 1024 * 1024  # 1GB max file size for download
    
    # Path validation settings
    MAX_PATH_LENGTH: int = 4096
    MAX_FILENAME_LENGTH: int = 255
    
    # Allowed file extensions (empty list = allow all)
    ALLOWED_EXTENSIONS: List[str] = []
    BLOCKED_EXTENSIONS: List[str] = [
        '.exe', '.dll', '.bat', '.cmd', '.sh', '.php',
        '.py', '.rb', '.pl', '.cgi'
    ]
    
    # Logging settings
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    @classmethod
    def from_environment(cls):
        """Load configuration from environment variables."""
        config = cls()
        
        # Override with environment variables if present
        if 'FILE_API_ROOT_DIR' in os.environ:
            config.ROOT_DIRECTORY = os.environ['FILE_API_ROOT_DIR']
        
        if 'FILE_API_ALLOW_HIDDEN' in os.environ:
            config.ALLOW_HIDDEN_FILES = os.environ['FILE_API_ALLOW_HIDDEN'].lower() == 'true'
        
        if 'FILE_API_REQUIRE_AUTH' in os.environ:
            config.REQUIRE_AUTHENTICATION = os.environ['FILE_API_REQUIRE_AUTH'].lower() == 'true'
        
        if 'FILE_API_SECRET_KEY' in os.environ:
            config.SECRET_KEY = os.environ['FILE_API_SECRET_KEY']
        
        if 'FILE_API_ALLOWED_ORIGINS' in os.environ:
            config.ALLOWED_ORIGINS = os.environ['FILE_API_ALLOWED_ORIGINS'].split(',')
        
        if 'FILE_API_LOG_LEVEL' in os.environ:
            config.LOG_LEVEL = os.environ['FILE_API_LOG_LEVEL']
        
        return config
    
    @classmethod
    def for_development(cls):
        """Get development configuration with relaxed settings."""
        config = cls()
        config.ALLOW_HIDDEN_FILES = True
        config.REQUIRE_AUTHENTICATION = False
        config.LOG_LEVEL = "DEBUG"
        return config
    
    @classmethod
    def for_production(cls, secret_key: str):
        """Get production configuration with strict settings."""
        config = cls()
        config.ALLOW_HIDDEN_FILES = False
        config.REQUIRE_AUTHENTICATION = True
        config.SECRET_KEY = secret_key
        config.LOG_LEVEL = "WARNING"
        config.ALLOWED_ORIGINS = []  # Must be explicitly set
        return config
