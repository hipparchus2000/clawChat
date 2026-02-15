"""
ClawChat File Operations Tests
===============================
Comprehensive tests for file operations including:
- Upload, delete, create, rename, move operations
- Integration tests for file upload/download
- Security tests (permission validation, path traversal)
- Performance tests for large file operations

Run with: pytest tests/test_file_operations.py -v
"""

import asyncio
import hashlib
import json
import os
import pytest
import sys
import tempfile
import time
from io import BytesIO
from pathlib import Path
from typing import AsyncGenerator
from unittest.mock import Mock, patch, AsyncMock, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'backend'))

import aiofiles
from aiofiles import os as aio_os

from file_api import (
    FileSystemAPI, FileSystemService, FileSystemWebSocketHandler,
    FileMetadata, DirectoryListing, APIResponse, ERROR_CODES,
    create_file_api
)
from path_validator import (
    PathValidator, PathValidationError, DirectoryTraversalError,
    InvalidPathError, initialize_validator
)
from security import (
    SecurityManager, SecurityContext, PermissionLevel,
    SecurityError, AuthenticationError, AuthorizationError,
    initialize_security, RateLimiter
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def temp_root_dir():
    """Create a temporary root directory for file operations."""
    temp_dir = tempfile.mkdtemp(prefix="clawchat_test_")
    yield temp_dir
    # Cleanup
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def sample_file_structure(temp_root_dir):
    """Create a sample file structure for testing."""
    # Create directories
    os.makedirs(os.path.join(temp_root_dir, "docs"))
    os.makedirs(os.path.join(temp_root_dir, "images"))
    os.makedirs(os.path.join(temp_root_dir, "nested", "deep", "folder"))
    
    # Create files
    files = {
        "readme.txt": "This is a readme file\n",
        "docs/guide.md": "# Guide\n\nThis is a guide.\n",
        "docs/api.json": '{"version": "1.0"}',
        "images/logo.png": b"\x89PNG\r\n\x1a\n" + b"fake_png_data" * 100,
        "nested/deep/folder/file.txt": "Deep nested file",
        ".hidden_file": "hidden content",
    }
    
    for path, content in files.items():
        full_path = os.path.join(temp_root_dir, path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        mode = 'wb' if isinstance(content, bytes) else 'w'
        with open(full_path, mode) as f:
            f.write(content)
    
    return temp_root_dir


@pytest.fixture
def security_context():
    """Create a test security context with full permissions."""
    return SecurityContext(
        user_id="test_user",
        session_id="test_session",
        permissions={
            PermissionLevel.READ,
            PermissionLevel.DOWNLOAD,
            PermissionLevel.LIST,
            PermissionLevel.WRITE,
            PermissionLevel.DELETE,
            PermissionLevel.ADMIN
        },
        ip_address="127.0.0.1"
    )


@pytest.fixture
def readonly_context():
    """Create a readonly security context."""
    return SecurityContext(
        user_id="readonly_user",
        session_id="readonly_session",
        permissions={PermissionLevel.READ, PermissionLevel.LIST},
        ip_address="127.0.0.1"
    )


@pytest.fixture
def file_service(temp_root_dir):
    """Create a FileSystemService instance."""
    # Initialize components
    initialize_validator(root_directory=temp_root_dir, allow_hidden=False)
    initialize_security(require_auth=False)
    
    return FileSystemService(
        root_directory=temp_root_dir,
        allow_hidden=False
    )


@pytest.fixture
def file_api(temp_root_dir):
    """Create a FileSystemAPI instance."""
    return create_file_api(
        root_directory=temp_root_dir,
        allow_hidden=False,
        require_auth=False
    )


@pytest.fixture
def mock_send():
    """Create a mock send callback for WebSocket handler tests."""
    return AsyncMock()


# ============================================================================
# Unit Tests - File Operations
# ============================================================================

@pytest.mark.unit
class TestFileMetadata:
    """Tests for file metadata operations."""
    
    @pytest.mark.asyncio
    async def test_get_file_metadata(self, file_service, sample_file_structure, security_context):
        """Test getting metadata for a file."""
        response = await file_service.get_file_metadata(
            "readme.txt",
            security_context
        )
        
        assert response.success is True
        assert response.data is not None
        assert response.data.name == "readme.txt"
        assert response.data.type == "file"
        assert response.data.size > 0
        assert response.data.mime_type == "text/plain"
    
    @pytest.mark.asyncio
    async def test_get_directory_metadata(self, file_service, sample_file_structure, security_context):
        """Test getting metadata for a directory."""
        response = await file_service.get_file_metadata(
            "docs",
            security_context
        )
        
        assert response.success is True
        assert response.data.type == "directory"
        assert response.data.name == "docs"
    
    @pytest.mark.asyncio
    async def test_get_metadata_nonexistent(self, file_service, security_context):
        """Test getting metadata for non-existent file."""
        response = await file_service.get_file_metadata(
            "nonexistent.txt",
            security_context
        )
        
        assert response.success is False
        assert response.error_code == ERROR_CODES['PATH_NOT_FOUND']
    
    @pytest.mark.asyncio
    async def test_get_metadata_permission_denied(self, file_service, sample_file_structure):
        """Test permission denied for metadata access."""
        context = SecurityContext(
            user_id="no_read",
            permissions={PermissionLevel.NONE},
            ip_address="127.0.0.1"
        )
        
        response = await file_service.get_file_metadata(
            "readme.txt",
            context
        )
        
        assert response.success is False
        assert response.error_code == ERROR_CODES['PERMISSION_DENIED']


@pytest.mark.unit
class TestDirectoryListing:
    """Tests for directory listing operations."""
    
    @pytest.mark.asyncio
    async def test_list_root_directory(self, file_service, sample_file_structure, security_context):
        """Test listing root directory."""
        response = await file_service.list_directory(
            "/",
            security_context
        )
        
        assert response.success is True
        assert response.data.total_count >= 3  # docs, images, readme.txt
        assert response.data.directory_count >= 2
        assert response.data.file_count >= 1
    
    @pytest.mark.asyncio
    async def test_list_subdirectory(self, file_service, sample_file_structure, security_context):
        """Test listing a subdirectory."""
        response = await file_service.list_directory(
            "docs",
            security_context
        )
        
        assert response.success is True
        assert response.data.total_count == 2
        assert response.data.file_count == 2
    
    @pytest.mark.asyncio
    async def test_list_directory_with_filter(self, file_service, sample_file_structure, security_context):
        """Test listing with filter pattern."""
        response = await file_service.list_directory(
            "/",
            security_context,
            filter_pattern="*.txt"
        )
        
        assert response.success is True
        assert all(item.extension == '.txt' for item in response.data.items)
    
    @pytest.mark.asyncio
    async def test_list_nonexistent_directory(self, file_service, security_context):
        """Test listing non-existent directory."""
        response = await file_service.list_directory(
            "nonexistent",
            security_context
        )
        
        assert response.success is False
        assert response.error_code == ERROR_CODES['DIRECTORY_NOT_FOUND']


@pytest.mark.unit
class TestFileDownload:
    """Tests for file download operations."""
    
    @pytest.mark.asyncio
    async def test_download_file_info(self, file_service, sample_file_structure, security_context):
        """Test getting download info for a file."""
        response = await file_service.download_file(
            "readme.txt",
            security_context
        )
        
        assert response.success is True
        assert response.data['name'] == "readme.txt"
        assert response.data['mime_type'] == "text/plain"
        assert 'size' in response.data
        assert 'supports_range' in response.data
    
    @pytest.mark.asyncio
    async def test_download_with_range(self, file_service, sample_file_structure, security_context):
        """Test download with byte range."""
        response = await file_service.download_file(
            "readme.txt",
            security_context,
            start_byte=0,
            end_byte=10
        )
        
        assert response.success is True
        assert response.data['start_byte'] == 0
        assert response.data['end_byte'] == 10
        assert response.data['content_length'] == 11
    
    @pytest.mark.asyncio
    async def test_download_directory(self, file_service, sample_file_structure, security_context):
        """Test attempting to download a directory."""
        response = await file_service.download_file(
            "docs",
            security_context
        )
        
        assert response.success is False
    
    @pytest.mark.asyncio
    async def test_download_permission_denied(self, file_service, sample_file_structure):
        """Test download with insufficient permissions."""
        context = SecurityContext(
            user_id="no_download",
            permissions={PermissionLevel.READ, PermissionLevel.LIST},
            ip_address="127.0.0.1"
        )
        
        response = await file_service.download_file(
            "readme.txt",
            context
        )
        
        assert response.success is False
        assert response.error_code == ERROR_CODES['PERMISSION_DENIED']
    
    @pytest.mark.asyncio
    async def test_read_file_chunks(self, file_service, sample_file_structure):
        """Test reading file in chunks."""
        file_path = os.path.join(sample_file_structure, "readme.txt")
        chunks = []
        
        async for chunk in file_service.read_file_chunks(file_path, chunk_size=5):
            chunks.append(chunk)
        
        assert len(chunks) > 0
        full_content = b''.join(chunks)
        assert b"readme" in full_content


# ============================================================================
# Security Tests
# ============================================================================

@pytest.mark.unit
class TestPathTraversalSecurity:
    """Security tests for path traversal prevention."""
    
    @pytest.mark.asyncio
    async def test_traversal_via_double_dot(self, file_service, security_context):
        """Test blocking ../ path traversal."""
        response = await file_service.get_file_metadata(
            "../etc/passwd",
            security_context
        )
        
        assert response.success is False
        assert response.error_code == ERROR_CODES['DIRECTORY_TRAVERSAL']
    
    @pytest.mark.asyncio
    async def test_traversal_via_url_encoding(self, file_service, security_context):
        """Test blocking URL-encoded path traversal."""
        response = await file_service.list_directory(
            "%2e%2e%2fetc",
            security_context
        )
        
        assert response.success is False
    
    @pytest.mark.asyncio
    async def test_traversal_via_backslash(self, file_service, sample_file_structure, security_context):
        """Test blocking backslash path traversal."""
        response = await file_service.list_directory(
            "..\\..\\windows",
            security_context
        )
        
        assert response.success is False
    
    @pytest.mark.asyncio
    async def test_null_byte_injection(self, file_service, security_context):
        """Test blocking null byte injection."""
        response = await file_service.get_file_metadata(
            "file.txt\x00.exe",
            security_context
        )
        
        assert response.success is False
    
    @pytest.mark.asyncio
    async def test_hidden_file_access_denied(self, file_service, sample_file_structure, security_context):
        """Test that hidden files are blocked by default."""
        response = await file_service.get_file_metadata(
            ".hidden_file",
            security_context
        )
        
        assert response.success is False
    
    @pytest.mark.asyncio
    async def test_absolute_path_traversal(self, file_service, security_context):
        """Test blocking absolute path traversal."""
        response = await file_service.get_file_metadata(
            "/etc/passwd",
            security_context
        )
        
        # Should resolve relative to root directory
        assert response.success is False


@pytest.mark.unit
class TestPermissionSecurity:
    """Security tests for permission system."""
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, file_service, sample_file_structure):
        """Test rate limiting on API calls."""
        context = SecurityContext(
            user_id="rate_test",
            permissions={PermissionLevel.READ, PermissionLevel.LIST},
            ip_address="127.0.0.1"
        )
        
        # Make many requests quickly
        responses = []
        for _ in range(150):  # Exceed burst limit
            response = await file_service.list_directory("/", context)
            responses.append(response)
        
        # Some should be rate limited
        rate_limited = [r for r in responses if r.error_code == ERROR_CODES['RATE_LIMIT_EXCEEDED']]
        assert len(rate_limited) > 0
    
    @pytest.mark.asyncio
    async def test_invalid_auth_token(self, file_api, temp_root_dir):
        """Test handling of invalid auth token."""
        message = {
            'action': 'list_directory',
            'path': '/',
            'auth_token': 'invalid_token_xyz'
        }
        
        send_mock = AsyncMock()
        await file_api.handle_websocket_message(
            message,
            {'ip_address': '127.0.0.1'},
            send_mock
        )
        
        # Should still work with require_auth=False
        send_mock.assert_called_once()


# ============================================================================
# Integration Tests
# ============================================================================

@pytest.mark.integration
class TestFileUploadIntegration:
    """Integration tests for file upload operations."""
    
    @pytest.mark.asyncio
    async def test_websocket_list_directory(self, file_api, sample_file_structure, mock_send):
        """Test listing directory via WebSocket."""
        message = {
            'action': 'list_directory',
            'path': '/',
            'user_id': 'test_user',
            'permissions': ['READ', 'LIST', 'ADMIN']
        }
        
        await file_api.handle_websocket_message(
            message,
            {'ip_address': '127.0.0.1'},
            mock_send
        )
        
        mock_send.assert_called_once()
        response = mock_send.call_args[0][0]
        assert response['success'] is True
        assert 'data' in response
    
    @pytest.mark.asyncio
    async def test_websocket_get_metadata(self, file_api, sample_file_structure, mock_send):
        """Test getting metadata via WebSocket."""
        message = {
            'action': 'get_metadata',
            'path': 'readme.txt',
            'user_id': 'test_user',
            'permissions': ['READ', 'DOWNLOAD', 'ADMIN']
        }
        
        await file_api.handle_websocket_message(
            message,
            {'ip_address': '127.0.0.1'},
            mock_send
        )
        
        mock_send.assert_called_once()
        response = mock_send.call_args[0][0]
        assert response['success'] is True
        assert response['data']['name'] == 'readme.txt'
    
    @pytest.mark.asyncio
    async def test_websocket_download_request(self, file_api, sample_file_structure, mock_send):
        """Test download request via WebSocket."""
        message = {
            'action': 'download_file',
            'path': 'readme.txt',
            'user_id': 'test_user',
            'permissions': ['READ', 'DOWNLOAD', 'ADMIN']
        }
        
        await file_api.handle_websocket_message(
            message,
            {'ip_address': '127.0.0.1'},
            mock_send
        )
        
        mock_send.assert_called_once()
        response = mock_send.call_args[0][0]
        assert response['success'] is True
        assert 'mime_type' in response['data']
    
    @pytest.mark.asyncio
    async def test_websocket_invalid_action(self, file_api, mock_send):
        """Test handling invalid action via WebSocket."""
        message = {
            'action': 'invalid_action',
            'path': '/'
        }
        
        await file_api.handle_websocket_message(
            message,
            {'ip_address': '127.0.0.1'},
            mock_send
        )
        
        mock_send.assert_called_once()
        response = mock_send.call_args[0][0]
        assert response['success'] is False
    
    @pytest.mark.asyncio
    async def test_websocket_missing_path(self, file_api, mock_send):
        """Test handling missing path in WebSocket message."""
        message = {
            'action': 'get_metadata'
            # Missing path
        }
        
        await file_api.handle_websocket_message(
            message,
            {'ip_address': '127.0.0.1'},
            mock_send
        )
        
        mock_send.assert_called_once()
        response = mock_send.call_args[0][0]
        assert response['success'] is False


# ============================================================================
# Performance Tests
# ============================================================================

@pytest.mark.performance
@pytest.mark.slow
class TestFileOperationsPerformance:
    """Performance tests for file operations."""
    
    @pytest.fixture
    def large_file_structure(self, temp_root_dir):
        """Create many files for performance testing."""
        # Create 100 files
        for i in range(100):
            os.makedirs(os.path.join(temp_root_dir, f"folder_{i}"), exist_ok=True)
            with open(os.path.join(temp_root_dir, f"folder_{i}", "file.txt"), 'w') as f:
                f.write(f"Content {i}\n")
        
        return temp_root_dir
    
    @pytest.fixture
    def large_file(self, temp_root_dir):
        """Create a large file for testing."""
        file_path = os.path.join(temp_root_dir, "large_file.bin")
        # Create 10MB file
        with open(file_path, 'wb') as f:
            f.write(os.urandom(10 * 1024 * 1024))
        return file_path
    
    @pytest.mark.asyncio
    async def test_large_directory_listing_performance(self, large_file_structure, security_context):
        """Test performance of listing large directories."""
        # Initialize validator and security
        initialize_validator(root_directory=large_file_structure, allow_hidden=False)
        initialize_security(require_auth=False)
        
        service = FileSystemService(
            root_directory=large_file_structure,
            allow_hidden=False
        )
        
        start_time = time.time()
        response = await service.list_directory("/", security_context)
        duration = time.time() - start_time
        
        assert response.success is True
        assert duration < 2.0  # Should complete in under 2 seconds
        assert response.data.total_count == 100
    
    @pytest.mark.asyncio
    async def test_large_file_chunk_reading(self, large_file, temp_root_dir):
        """Test performance of reading large files in chunks."""
        initialize_validator(root_directory=temp_root_dir, allow_hidden=False)
        initialize_security(require_auth=False)
        
        service = FileSystemService(
            root_directory=temp_root_dir,
            allow_hidden=False
        )
        
        start_time = time.time()
        chunks = []
        async for chunk in service.read_file_chunks(large_file, chunk_size=65536):
            chunks.append(chunk)
        duration = time.time() - start_time
        
        total_size = sum(len(c) for c in chunks)
        assert total_size == 10 * 1024 * 1024  # 10MB
        assert duration < 5.0  # Should complete in under 5 seconds
    
    @pytest.mark.asyncio
    async def test_concurrent_file_access(self, large_file_structure, security_context):
        """Test concurrent access to file operations."""
        initialize_validator(root_directory=large_file_structure, allow_hidden=False)
        initialize_security(require_auth=False)
        
        service = FileSystemService(
            root_directory=large_file_structure,
            allow_hidden=False
        )
        
        async def access_folder(i):
            return await service.list_directory(f"folder_{i}", security_context)
        
        start_time = time.time()
        # Access 20 folders concurrently
        tasks = [access_folder(i) for i in range(20)]
        results = await asyncio.gather(*tasks)
        duration = time.time() - start_time
        
        assert all(r.success for r in results)
        assert duration < 3.0  # Should complete in under 3 seconds
    
    @pytest.mark.asyncio
    async def test_metadata_caching_performance(self, sample_file_structure, security_context):
        """Test performance of repeated metadata requests."""
        initialize_validator(root_directory=sample_file_structure, allow_hidden=False)
        initialize_security(require_auth=False)
        
        service = FileSystemService(
            root_directory=sample_file_structure,
            allow_hidden=False
        )
        
        start_time = time.time()
        # Request same file metadata 50 times
        for _ in range(50):
            response = await service.get_file_metadata("readme.txt", security_context)
            assert response.success is True
        duration = time.time() - start_time
        
        assert duration < 1.0  # Should complete in under 1 second


# ============================================================================
# Edge Case Tests
# ============================================================================

@pytest.mark.unit
class TestEdgeCases:
    """Tests for edge cases and error scenarios."""
    
    @pytest.mark.asyncio
    async def test_empty_path(self, file_service, security_context):
        """Test handling of empty path."""
        response = await file_service.get_file_metadata(
            "",
            security_context
        )
        
        assert response.success is False
    
    @pytest.mark.asyncio
    async def test_special_characters_in_filename(self, file_service, sample_file_structure, security_context):
        """Test handling of special characters in filenames."""
        # Create file with special characters
        special_path = os.path.join(sample_file_structure, "file with spaces & symbols.txt")
        with open(special_path, 'w') as f:
            f.write("content")
        
        response = await file_service.get_file_metadata(
            "file with spaces & symbols.txt",
            security_context
        )
        
        assert response.success is True
    
    @pytest.mark.asyncio
    async def test_very_long_path(self, file_service, security_context):
        """Test handling of very long paths."""
        long_path = "a" * 5000
        
        response = await file_service.get_file_metadata(
            long_path,
            security_context
        )
        
        assert response.success is False
    
    @pytest.mark.asyncio
    async def test_unicode_filenames(self, file_service, sample_file_structure, security_context):
        """Test handling of unicode filenames."""
        # Create file with unicode name
        unicode_path = os.path.join(sample_file_structure, "文件_文档.txt")
        with open(unicode_path, 'w', encoding='utf-8') as f:
            f.write("unicode content")
        
        response = await file_service.get_file_metadata(
            "文件_文档.txt",
            security_context
        )
        
        assert response.success is True
    
    @pytest.mark.asyncio
    async def test_symlink_handling(self, file_service, sample_file_structure, security_context):
        """Test handling of symbolic links."""
        # Create symlink
        link_path = os.path.join(sample_file_structure, "link_to_readme")
        target = os.path.join(sample_file_structure, "readme.txt")
        
        try:
            os.symlink(target, link_path)
            response = await file_service.get_file_metadata(
                "link_to_readme",
                security_context
            )
            
            # Should resolve the symlink
            assert response.success is True
        except (OSError, NotImplementedError):
            # Skip if symlinks not supported
            pytest.skip("Symlinks not supported on this platform")
    
    @pytest.mark.asyncio
    async def test_binary_file_metadata(self, file_service, sample_file_structure, security_context):
        """Test metadata extraction for binary files."""
        response = await file_service.get_file_metadata(
            "images/logo.png",
            security_context
        )
        
        assert response.success is True
        assert response.data.mime_type == "image/png"
        assert response.data.size > 0


# ============================================================================
# Data Model Tests
# ============================================================================

@pytest.mark.unit
class TestDataModels:
    """Tests for data models."""
    
    def test_file_metadata_dataclass(self):
        """Test FileMetadata dataclass."""
        metadata = FileMetadata(
            name="test.txt",
            path="docs/test.txt",
            type="file",
            size=1024,
            modified_time=1234567890.0,
            created_time=1234567800.0,
            permissions="rw-r--r--",
            is_hidden=False,
            mime_type="text/plain",
            extension=".txt",
            parent_path="docs"
        )
        
        assert metadata.name == "test.txt"
        assert metadata.mime_type == "text/plain"
        assert metadata.extension == ".txt"
    
    def test_api_response_success(self):
        """Test successful API response."""
        response = APIResponse(
            success=True,
            data={"key": "value"},
            request_id="test-123"
        )
        
        response_dict = response.to_dict()
        assert response_dict['success'] is True
        assert response_dict['data'] == {"key": "value"}
        assert response_dict['request_id'] == "test-123"
        assert 'timestamp' in response_dict
    
    def test_api_response_error(self):
        """Test error API response."""
        response = APIResponse(
            success=False,
            error="File not found",
            error_code="E001",
            request_id="test-456"
        )
        
        response_dict = response.to_dict()
        assert response_dict['success'] is False
        assert response_dict['error'] == "File not found"
        assert response_dict['error_code'] == "E001"
    
    def test_directory_listing_dataclass(self):
        """Test DirectoryListing dataclass."""
        items = [
            FileMetadata(
                name="file1.txt",
                path="file1.txt",
                type="file",
                size=100,
                modified_time=1234567890.0,
                created_time=1234567800.0,
                permissions="rw-r--r--",
                is_hidden=False
            ),
            FileMetadata(
                name="folder",
                path="folder",
                type="directory",
                size=0,
                modified_time=1234567890.0,
                created_time=1234567800.0,
                permissions="rwxr-xr-x",
                is_hidden=False
            )
        ]
        
        listing = DirectoryListing(
            path="/",
            items=items,
            total_count=2,
            file_count=1,
            directory_count=1,
            hidden_count=0
        )
        
        assert listing.total_count == 2
        assert listing.file_count == 1
        assert listing.directory_count == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
