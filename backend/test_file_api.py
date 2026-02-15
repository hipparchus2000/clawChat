"""
ClawChat File System API - Test Suite
=====================================
Test suite for the file system API components.
"""

import asyncio
import os
import tempfile
import pytest
from pathlib import Path

from path_validator import PathValidator, DirectoryTraversalError, InvalidPathError, initialize_validator
from security import SecurityManager, SecurityContext, PermissionLevel, initialize_security
from file_api import FileSystemAPI, FileSystemService, create_file_api


class TestPathValidator:
    """Test cases for PathValidator."""
    
    @pytest.fixture
    def validator(self):
        """Create a test validator with temp directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield PathValidator(root_directory=tmpdir, allow_hidden=False)
    
    def test_valid_path(self, validator):
        """Test validation of valid paths."""
        # Create a test file
        test_file = Path(validator.root_directory) / "test.txt"
        test_file.write_text("test")
        
        result = validator.validate("test.txt")
        assert result.name == "test.txt"
    
    def test_directory_traversal_basic(self, validator):
        """Test detection of basic directory traversal."""
        with pytest.raises(DirectoryTraversalError):
            validator.validate("../etc/passwd")
    
    def test_directory_traversal_encoded(self, validator):
        """Test detection of URL-encoded traversal."""
        with pytest.raises(DirectoryTraversalError):
            validator.validate("%2e%2e%2fetc/passwd")
    
    def test_directory_traversal_double_dot(self, validator):
        """Test detection of double-dot traversal."""
        with pytest.raises(DirectoryTraversalError):
            validator.validate("folder/../../etc/passwd")
    
    def test_hidden_files_blocked(self, validator):
        """Test that hidden files are blocked by default."""
        with pytest.raises(InvalidPathError):
            validator.validate(".hidden_file")
    
    def test_hidden_files_allowed(self):
        """Test that hidden files can be allowed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            validator = PathValidator(root_directory=tmpdir, allow_hidden=True)
            test_file = Path(tmpdir) / ".hidden"
            test_file.write_text("secret")
            
            result = validator.validate(".hidden")
            assert result.name == ".hidden"
    
    def test_path_too_long(self, validator):
        """Test detection of overly long paths."""
        with pytest.raises(InvalidPathError):
            validator.validate("a" * 5000)
    
    def test_null_bytes_rejected(self, validator):
        """Test that null bytes are rejected."""
        with pytest.raises(InvalidPathError):
            validator.validate("file\x00.txt")
    
    def test_sanitize_filename(self, validator):
        """Test filename sanitization."""
        assert validator.sanitize_filename("../../../etc/passwd") == "etc_passwd"
        assert validator.sanitize_filename("file\x00.txt") == "file.txt"
        assert validator.sanitize_filename("test<file>.txt") == "test_file_.txt"


class TestSecurityManager:
    """Test cases for SecurityManager."""
    
    @pytest.fixture
    def security(self):
        """Create a test security manager."""
        return SecurityManager(secret_key="test_secret", require_auth=False)
    
    @pytest.fixture
    def context(self, security):
        """Create a test security context."""
        return security.create_context(
            user_id="test_user",
            ip_address="127.0.0.1",
            permissions=[PermissionLevel.READ, PermissionLevel.LIST]
        )
    
    def test_context_creation(self, security):
        """Test security context creation."""
        context = security.create_context(user_id="user1")
        assert context.user_id == "user1"
        assert PermissionLevel.READ in context.permissions
    
    def test_permission_check(self, security, context):
        """Test permission checking."""
        assert context.can_read() is True
        assert context.can_list() is True
        assert context.can_write() is False
        assert context.can_delete() is False
    
    @pytest.mark.asyncio
    async def test_rate_limiter(self, security):
        """Test rate limiting."""
        limiter = security.list_rate_limiter
        
        # Should allow requests within limit
        key = "test_client"
        for _ in range(10):
            assert await limiter.is_allowed(key) is True
        
        # Track remaining
        remaining = await limiter.get_remaining(key)
        assert remaining >= 0
    
    def test_origin_validation(self, security):
        """Test CORS origin validation."""
        security.allowed_origins = ["https://example.com"]
        assert security.validate_origin("https://example.com") is True
        assert security.validate_origin("https://evil.com") is False
        
        # Wildcard allows all
        security.allowed_origins = ["*"]
        assert security.validate_origin("https://anything.com") is True
    
    def test_request_sanitization(self, security):
        """Test request data sanitization."""
        data = {
            "path": "../../../etc/passwd\x00",
            "nested": {"key": "value\x00"},
            "number": 42
        }
        
        sanitized = security.sanitize_request_data(data)
        assert "\x00" not in sanitized["path"]
        assert "\x00" not in sanitized["nested"]["key"]
        assert sanitized["number"] == 42


class TestFileSystemService:
    """Test cases for FileSystemService."""
    
    @pytest.fixture
    async def service(self):
        """Create a test file service."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Initialize components
            initialize_validator(root_directory=tmpdir, allow_hidden=False)
            initialize_security(require_auth=False)
            
            # Create test files
            (Path(tmpdir) / "file1.txt").write_text("Hello, World!")
            (Path(tmpdir) / "file2.txt").write_text("Second file")
            (Path(tmpdir) / "subdir").mkdir()
            (Path(tmpdir) / "subdir" / "nested.txt").write_text("Nested content")
            
            api = FileSystemAPI(root_directory=tmpdir, allow_hidden=False)
            yield api.file_service
    
    @pytest.fixture
    def context(self):
        """Create a test security context."""
        security = get_security_manager()
        return security.create_context(
            user_id="test_user",
            permissions=[PermissionLevel.READ, PermissionLevel.LIST, PermissionLevel.DOWNLOAD]
        )
    
    @pytest.mark.asyncio
    async def test_list_directory(self, service, context):
        """Test directory listing."""
        response = await service.list_directory("/", context)
        
        assert response.success is True
        assert response.data is not None
        assert response.data.total_count >= 3  # 2 files + 1 subdir
    
    @pytest.mark.asyncio
    async def test_list_subdirectory(self, service, context):
        """Test subdirectory listing."""
        response = await service.list_directory("subdir", context)
        
        assert response.success is True
        assert response.data.total_count == 1
        assert response.data.items[0].name == "nested.txt"
    
    @pytest.mark.asyncio
    async def test_get_file_metadata(self, service, context):
        """Test file metadata retrieval."""
        response = await service.get_file_metadata("file1.txt", context)
        
        assert response.success is True
        assert response.data.name == "file1.txt"
        assert response.data.type == "file"
        assert response.data.size == 13  # "Hello, World!"
    
    @pytest.mark.asyncio
    async def test_get_directory_metadata(self, service, context):
        """Test directory metadata retrieval."""
        response = await service.get_file_metadata("subdir", context)
        
        assert response.success is True
        assert response.data.type == "directory"
    
    @pytest.mark.asyncio
    async def test_download_file(self, service, context):
        """Test file download preparation."""
        response = await service.download_file("file1.txt", context)
        
        assert response.success is True
        assert response.data['name'] == "file1.txt"
        assert response.data['mime_type'] == "text/plain"
        assert response.data['size'] == 13
    
    @pytest.mark.asyncio
    async def test_download_directory_fails(self, service, context):
        """Test that downloading a directory fails."""
        response = await service.download_file("subdir", context)
        
        assert response.success is False
    
    @pytest.mark.asyncio
    async def test_directory_traversal_blocked(self, service, context):
        """Test that directory traversal is blocked."""
        response = await service.list_directory("../", context)
        
        assert response.success is False
        assert "traversal" in response.error.lower()
    
    @pytest.mark.asyncio
    async def test_file_not_found(self, service, context):
        """Test handling of non-existent files."""
        response = await service.get_file_metadata("nonexistent.txt", context)
        
        assert response.success is False
        assert response.error_code is not None


class TestFileSystemAPI:
    """Integration tests for the full FileSystemAPI."""
    
    @pytest.fixture
    def api(self):
        """Create a test API instance."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test structure
            (Path(tmpdir) / "docs").mkdir()
            (Path(tmpdir) / "docs" / "readme.txt").write_text("Documentation")
            (Path(tmpdir) / "data.json").write_text('{"key": "value"}')
            
            yield create_file_api(
                root_directory=tmpdir,
                allow_hidden=False,
                require_auth=False
            )
    
    @pytest.mark.asyncio
    async def test_websocket_message_handling(self, api):
        """Test WebSocket message handling."""
        messages = []
        
        async def send_callback(data):
            messages.append(data)
        
        client_info = {'ip_address': '127.0.0.1'}
        
        # Test list_directory
        message = {
            'action': 'list_directory',
            'path': '/'
        }
        
        await api.handle_websocket_message(message, client_info, send_callback)
        
        assert len(messages) == 1
        assert messages[0]['success'] is True
        assert messages[0]['data']['total_count'] == 2
    
    @pytest.mark.asyncio
    async def test_websocket_metadata_request(self, api):
        """Test metadata request via WebSocket."""
        messages = []
        
        async def send_callback(data):
            messages.append(data)
        
        client_info = {'ip_address': '127.0.0.1'}
        
        message = {
            'action': 'get_metadata',
            'path': 'data.json'
        }
        
        await api.handle_websocket_message(message, client_info, send_callback)
        
        assert len(messages) == 1
        assert messages[0]['success'] is True
        assert messages[0]['data']['name'] == 'data.json'
    
    @pytest.mark.asyncio
    async def test_websocket_download_request(self, api):
        """Test download request via WebSocket."""
        messages = []
        
        async def send_callback(data):
            messages.append(data)
        
        client_info = {'ip_address': '127.0.0.1'}
        
        message = {
            'action': 'download_file',
            'path': 'data.json'
        }
        
        await api.handle_websocket_message(message, client_info, send_callback)
        
        assert len(messages) == 1
        assert messages[0]['success'] is True
        assert 'mime_type' in messages[0]['data']
    
    @pytest.mark.asyncio
    async def test_websocket_unknown_action(self, api):
        """Test handling of unknown actions."""
        messages = []
        
        async def send_callback(data):
            messages.append(data)
        
        client_info = {'ip_address': '127.0.0.1'}
        
        message = {
            'action': 'unknown_action'
        }
        
        await api.handle_websocket_message(message, client_info, send_callback)
        
        assert len(messages) == 1
        assert messages[0]['success'] is False
        assert 'unknown' in messages[0]['error'].lower()
    
    @pytest.mark.asyncio
    async def test_websocket_invalid_json(self, api):
        """Test handling of invalid JSON."""
        messages = []
        
        async def send_callback(data):
            messages.append(data)
        
        client_info = {'ip_address': '127.0.0.1'}
        
        await api.handle_websocket_message(
            "invalid json {{{",
            client_info,
            send_callback
        )
        
        assert len(messages) == 1
        assert messages[0]['success'] is False
        assert 'json' in messages[0]['error'].lower()


def run_tests():
    """Run the test suite."""
    pytest.main([__file__, "-v"])


if __name__ == "__main__":
    run_tests()
