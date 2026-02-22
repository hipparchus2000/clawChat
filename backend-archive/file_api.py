"""
ClawChat File System API - Main Module
======================================
Provides directory listing, file metadata, and download capabilities.
Integrates with WebSocket server architecture.
"""

import asyncio
import json
import logging
import mimetypes
import os
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable, Union
import aiofiles
from aiofiles import os as aio_os

from path_validator import (
    PathValidator, PathValidationError, DirectoryTraversalError,
    InvalidPathError, initialize_validator, get_validator
)
from security import (
    SecurityManager, SecurityContext, PermissionLevel,
    SecurityError, AuthenticationError, AuthorizationError, RateLimitError,
    initialize_security, get_security_manager
)

logger = logging.getLogger(__name__)


# ============== Data Models ==============

@dataclass
class FileMetadata:
    """Metadata for a file or directory."""
    name: str
    path: str
    type: str  # 'file' or 'directory'
    size: int
    modified_time: float
    created_time: float
    permissions: str
    is_hidden: bool
    mime_type: Optional[str] = None
    extension: Optional[str] = None
    parent_path: Optional[str] = None


@dataclass
class DirectoryListing:
    """Result of a directory listing operation."""
    path: str
    items: List[FileMetadata]
    total_count: int
    file_count: int
    directory_count: int
    hidden_count: int


@dataclass
class APIResponse:
    """Standard API response wrapper."""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    error_code: Optional[str] = None
    request_id: Optional[str] = None
    timestamp: float = None
    rate_limit_remaining: Optional[int] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().timestamp()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert response to dictionary."""
        result = {
            'success': self.success,
            'timestamp': self.timestamp,
            'request_id': self.request_id
        }
        
        if self.data is not None:
            if isinstance(self.data, (FileMetadata, DirectoryListing)):
                result['data'] = asdict(self.data)
            elif isinstance(self.data, list):
                result['data'] = [
                    asdict(item) if isinstance(item, (FileMetadata, DirectoryListing)) else item
                    for item in self.data
                ]
            else:
                result['data'] = self.data
        
        if self.error:
            result['error'] = self.error
        
        if self.error_code:
            result['error_code'] = self.error_code
        
        if self.rate_limit_remaining is not None:
            result['rate_limit_remaining'] = self.rate_limit_remaining
        
        return result


# ============== Error Codes ==============

ERROR_CODES = {
    'PATH_NOT_FOUND': 'E001',
    'PERMISSION_DENIED': 'E002',
    'INVALID_PATH': 'E003',
    'DIRECTORY_TRAVERSAL': 'E004',
    'RATE_LIMIT_EXCEEDED': 'E005',
    'AUTHENTICATION_REQUIRED': 'E006',
    'AUTHORIZATION_FAILED': 'E007',
    'FILE_NOT_FOUND': 'E008',
    'DIRECTORY_NOT_FOUND': 'E009',
    'INTERNAL_ERROR': 'E999'
}


# ============== File System Service ==============

class FileSystemService:
    """
    Core file system service providing async operations.
    """
    
    def __init__(
        self,
        root_directory: str,
        allow_hidden: bool = False,
        chunk_size: int = 8192
    ):
        self.root_directory = Path(root_directory).resolve()
        self.allow_hidden = allow_hidden
        self.chunk_size = chunk_size
        self.validator = get_validator()
        self.security = get_security_manager()
        
        logger.info(f"FileSystemService initialized with root: {self.root_directory}")
    
    def _is_hidden(self, path: Path) -> bool:
        """Check if a file or directory is hidden."""
        name = path.name
        return name.startswith('.')
    
    def _get_permissions_string(self, path: Path) -> str:
        """Get Unix-style permissions string."""
        try:
            stat = path.stat()
            mode = stat.st_mode
            
            perms = []
            # Owner
            perms.append('r' if mode & 0o400 else '-')
            perms.append('w' if mode & 0o200 else '-')
            perms.append('x' if mode & 0o100 else '-')
            # Group
            perms.append('r' if mode & 0o040 else '-')
            perms.append('w' if mode & 0o020 else '-')
            perms.append('x' if mode & 0o010 else '-')
            # Other
            perms.append('r' if mode & 0o004 else '-')
            perms.append('w' if mode & 0o002 else '-')
            perms.append('x' if mode & 0o001 else '-')
            
            return ''.join(perms)
        except Exception:
            return '---------'
    
    async def _get_file_metadata(self, path: Path, relative_to: Optional[Path] = None) -> FileMetadata:
        """Get metadata for a file or directory."""
        try:
            stat = await aio_os.stat(path)
            
            # Determine relative path
            if relative_to:
                try:
                    rel_path = str(path.relative_to(relative_to))
                except ValueError:
                    rel_path = str(path)
            else:
                rel_path = str(path.relative_to(self.root_directory))
            
            # Get parent path
            try:
                parent = str(path.parent.relative_to(self.root_directory))
            except ValueError:
                parent = ""
            
            is_file = path.is_file()
            mime_type = None
            extension = None
            
            if is_file:
                mime_type, _ = mimetypes.guess_type(str(path))
                extension = path.suffix.lower() if path.suffix else None
            
            return FileMetadata(
                name=path.name,
                path=rel_path,
                type='file' if is_file else 'directory',
                size=stat.st_size if is_file else 0,
                modified_time=stat.st_mtime,
                created_time=stat.st_ctime,
                permissions=self._get_permissions_string(path),
                is_hidden=self._is_hidden(path),
                mime_type=mime_type,
                extension=extension,
                parent_path=parent if parent else None
            )
        except Exception as e:
            logger.error(f"Error getting metadata for {path}: {e}")
            raise
    
    async def list_directory(
        self,
        path: str,
        context: SecurityContext,
        include_hidden: Optional[bool] = None,
        filter_pattern: Optional[str] = None
    ) -> APIResponse:
        """
        List contents of a directory.
        
        Args:
            path: Directory path (relative to root)
            context: Security context
            include_hidden: Override default hidden file setting
            filter_pattern: Optional glob pattern to filter results
            
        Returns:
            APIResponse with DirectoryListing
        """
        request_id = context.session_id
        
        try:
            # Check rate limit
            allowed, remaining = await self.security.check_rate_limit(
                context, self.security.list_rate_limiter, "list_directory"
            )
            if not allowed:
                return APIResponse(
                    success=False,
                    error="Rate limit exceeded. Please try again later.",
                    error_code=ERROR_CODES['RATE_LIMIT_EXCEEDED'],
                    request_id=request_id,
                    rate_limit_remaining=0
                )
            
            # Check permission
            if not await self.security.check_permission(
                context, PermissionLevel.LIST, "list_directory"
            ):
                self.security.log_security_event(
                    'PERMISSION_DENIED', context, {'operation': 'list_directory', 'path': path}
                )
                return APIResponse(
                    success=False,
                    error="Permission denied: list access required",
                    error_code=ERROR_CODES['PERMISSION_DENIED'],
                    request_id=request_id,
                    rate_limit_remaining=remaining
                )
            
            # Validate path
            try:
                resolved_path = self.validator.validate_directory(path)
            except DirectoryTraversalError as e:
                self.security.log_security_event(
                    'DIRECTORY_TRAVERSAL_ATTEMPT', context, {'path': path}
                )
                return APIResponse(
                    success=False,
                    error="Invalid path: directory traversal detected",
                    error_code=ERROR_CODES['DIRECTORY_TRAVERSAL'],
                    request_id=request_id,
                    rate_limit_remaining=remaining
                )
            except InvalidPathError as e:
                return APIResponse(
                    success=False,
                    error=str(e),
                    error_code=ERROR_CODES['DIRECTORY_NOT_FOUND'],
                    request_id=request_id,
                    rate_limit_remaining=remaining
                )
            
            # Determine hidden file handling
            show_hidden = include_hidden if include_hidden is not None else self.allow_hidden
            
            # List directory contents
            items = []
            file_count = 0
            directory_count = 0
            hidden_count = 0
            
            try:
                entries = await aio_os.listdir(resolved_path)
            except PermissionError:
                return APIResponse(
                    success=False,
                    error="Permission denied: cannot access directory",
                    error_code=ERROR_CODES['PERMISSION_DENIED'],
                    request_id=request_id,
                    rate_limit_remaining=remaining
                )
            
            for entry in sorted(entries):
                entry_path = resolved_path / entry
                
                # Skip hidden files if not allowed
                is_hidden = entry.startswith('.')
                if is_hidden and not show_hidden:
                    hidden_count += 1
                    continue
                
                # Apply filter pattern
                if filter_pattern and not entry_path.match(filter_pattern):
                    continue
                
                try:
                    metadata = await self._get_file_metadata(entry_path, self.root_directory)
                    items.append(metadata)
                    
                    if metadata.type == 'file':
                        file_count += 1
                    else:
                        directory_count += 1
                        
                    if metadata.is_hidden:
                        hidden_count += 1
                        
                except Exception as e:
                    logger.warning(f"Could not get metadata for {entry_path}: {e}")
                    continue
            
            # Get relative path for response
            try:
                rel_path = str(resolved_path.relative_to(self.root_directory))
            except ValueError:
                rel_path = "/"
            
            listing = DirectoryListing(
                path=rel_path or "/",
                items=items,
                total_count=len(items),
                file_count=file_count,
                directory_count=directory_count,
                hidden_count=hidden_count
            )
            
            return APIResponse(
                success=True,
                data=listing,
                request_id=request_id,
                rate_limit_remaining=remaining
            )
            
        except Exception as e:
            logger.error(f"Error listing directory {path}: {e}")
            return APIResponse(
                success=False,
                error=f"Internal error: {str(e)}",
                error_code=ERROR_CODES['INTERNAL_ERROR'],
                request_id=request_id,
                rate_limit_remaining=remaining if 'remaining' in locals() else None
            )
    
    async def get_file_metadata(
        self,
        path: str,
        context: SecurityContext
    ) -> APIResponse:
        """
        Get metadata for a file or directory.
        
        Args:
            path: File or directory path
            context: Security context
            
        Returns:
            APIResponse with FileMetadata
        """
        request_id = context.session_id
        
        try:
            # Check rate limit
            allowed, remaining = await self.security.check_rate_limit(
                context, self.security.metadata_rate_limiter, "get_file_metadata"
            )
            if not allowed:
                return APIResponse(
                    success=False,
                    error="Rate limit exceeded. Please try again later.",
                    error_code=ERROR_CODES['RATE_LIMIT_EXCEEDED'],
                    request_id=request_id,
                    rate_limit_remaining=0
                )
            
            # Check permission
            if not await self.security.check_permission(
                context, PermissionLevel.READ, "get_file_metadata"
            ):
                return APIResponse(
                    success=False,
                    error="Permission denied: read access required",
                    error_code=ERROR_CODES['PERMISSION_DENIED'],
                    request_id=request_id,
                    rate_limit_remaining=remaining
                )
            
            # Validate path
            try:
                resolved_path = self.validator.validate(path)
            except DirectoryTraversalError:
                return APIResponse(
                    success=False,
                    error="Invalid path: directory traversal detected",
                    error_code=ERROR_CODES['DIRECTORY_TRAVERSAL'],
                    request_id=request_id,
                    rate_limit_remaining=remaining
                )
            except InvalidPathError as e:
                return APIResponse(
                    success=False,
                    error=str(e),
                    error_code=ERROR_CODES['PATH_NOT_FOUND'],
                    request_id=request_id,
                    rate_limit_remaining=remaining
                )
            
            # Check existence
            if not await aio_os.path.exists(resolved_path):
                return APIResponse(
                    success=False,
                    error="File or directory not found",
                    error_code=ERROR_CODES['PATH_NOT_FOUND'],
                    request_id=request_id,
                    rate_limit_remaining=remaining
                )
            
            # Get metadata
            metadata = await self._get_file_metadata(resolved_path, self.root_directory)
            
            return APIResponse(
                success=True,
                data=metadata,
                request_id=request_id,
                rate_limit_remaining=remaining
            )
            
        except Exception as e:
            logger.error(f"Error getting metadata for {path}: {e}")
            return APIResponse(
                success=False,
                error=f"Internal error: {str(e)}",
                error_code=ERROR_CODES['INTERNAL_ERROR'],
                request_id=request_id
            )
    
    async def download_file(
        self,
        path: str,
        context: SecurityContext,
        start_byte: int = 0,
        end_byte: Optional[int] = None
    ) -> APIResponse:
        """
        Prepare a file for download.
        
        Args:
            path: File path
            context: Security context
            start_byte: Starting byte for range requests
            end_byte: Ending byte for range requests
            
        Returns:
            APIResponse with download information
        """
        request_id = context.session_id
        
        try:
            # Check rate limit
            allowed, remaining = await self.security.check_rate_limit(
                context, self.security.download_rate_limiter, "download_file"
            )
            if not allowed:
                return APIResponse(
                    success=False,
                    error="Rate limit exceeded. Please try again later.",
                    error_code=ERROR_CODES['RATE_LIMIT_EXCEEDED'],
                    request_id=request_id,
                    rate_limit_remaining=0
                )
            
            # Check permission
            if not await self.security.check_permission(
                context, PermissionLevel.DOWNLOAD, "download_file"
            ):
                self.security.log_security_event(
                    'PERMISSION_DENIED', context, {'operation': 'download_file', 'path': path}
                )
                return APIResponse(
                    success=False,
                    error="Permission denied: download access required",
                    error_code=ERROR_CODES['PERMISSION_DENIED'],
                    request_id=request_id,
                    rate_limit_remaining=remaining
                )
            
            # Validate path
            try:
                resolved_path = self.validator.validate_file(path)
            except DirectoryTraversalError:
                return APIResponse(
                    success=False,
                    error="Invalid path: directory traversal detected",
                    error_code=ERROR_CODES['DIRECTORY_TRAVERSAL'],
                    request_id=request_id,
                    rate_limit_remaining=remaining
                )
            except InvalidPathError as e:
                return APIResponse(
                    success=False,
                    error=str(e),
                    error_code=ERROR_CODES['FILE_NOT_FOUND'],
                    request_id=request_id,
                    rate_limit_remaining=remaining
                )
            
            # Get file metadata
            metadata = await self._get_file_metadata(resolved_path, self.root_directory)
            
            # Validate byte range
            file_size = metadata.size
            
            if start_byte < 0:
                start_byte = 0
            
            if end_byte is None or end_byte >= file_size:
                end_byte = file_size - 1
            
            if start_byte > end_byte:
                return APIResponse(
                    success=False,
                    error="Invalid byte range",
                    error_code=ERROR_CODES['INVALID_PATH'],
                    request_id=request_id,
                    rate_limit_remaining=remaining
                )
            
            # Generate download info
            download_info = {
                'path': metadata.path,
                'name': metadata.name,
                'mime_type': metadata.mime_type or 'application/octet-stream',
                'size': file_size,
                'start_byte': start_byte,
                'end_byte': end_byte,
                'content_length': end_byte - start_byte + 1 if end_byte else file_size,
                'supports_range': True,
                'full_path': str(resolved_path)
            }
            
            return APIResponse(
                success=True,
                data=download_info,
                request_id=request_id,
                rate_limit_remaining=remaining
            )
            
        except Exception as e:
            logger.error(f"Error preparing download for {path}: {e}")
            return APIResponse(
                success=False,
                error=f"Internal error: {str(e)}",
                error_code=ERROR_CODES['INTERNAL_ERROR'],
                request_id=request_id
            )
    
    async def read_file_chunks(
        self,
        path: str,
        chunk_size: int = 8192,
        start_byte: int = 0,
        end_byte: Optional[int] = None
    ):
        """
        Async generator to read file in chunks.
        
        Args:
            path: Full file path
            chunk_size: Size of chunks to read
            start_byte: Starting byte position
            end_byte: Ending byte position (None = end of file)
            
        Yields:
            File chunks as bytes
        """
        try:
            async with aiofiles.open(path, 'rb') as f:
                # Seek to start position
                if start_byte > 0:
                    await f.seek(start_byte)
                
                bytes_remaining = end_byte - start_byte + 1 if end_byte else None
                
                while True:
                    # Adjust chunk size if we have a limit
                    current_chunk_size = chunk_size
                    if bytes_remaining is not None:
                        current_chunk_size = min(chunk_size, bytes_remaining)
                        if current_chunk_size <= 0:
                            break
                    
                    chunk = await f.read(current_chunk_size)
                    if not chunk:
                        break
                    
                    if bytes_remaining is not None:
                        bytes_remaining -= len(chunk)
                    
                    yield chunk
                    
        except Exception as e:
            logger.error(f"Error reading file {path}: {e}")
            raise


# ============== WebSocket Integration ==============

class FileSystemWebSocketHandler:
    """
    WebSocket handler for file system operations.
    Integrates with existing WebSocket server architecture.
    """
    
    def __init__(self, file_service: FileSystemService):
        self.file_service = file_service
        self.message_handlers = {
            'list_directory': self._handle_list_directory,
            'get_metadata': self._handle_get_metadata,
            'download_file': self._handle_download_file,
            'ping': self._handle_ping
        }
    
    def _create_context(self, message: Dict[str, Any], client_info: Dict[str, Any]) -> SecurityContext:
        """Create security context from message and client info."""
        security = get_security_manager()
        
        # Extract auth info from message
        auth_token = message.get('auth_token')
        user_id = message.get('user_id') or client_info.get('user_id')
        permissions = message.get('permissions', ['READ'])
        
        # Convert permission strings to enum
        perm_levels = []
        for perm in permissions:
            try:
                perm_levels.append(PermissionLevel[perm.upper()])
            except KeyError:
                pass
        
        return security.create_context(
            user_id=user_id,
            auth_token=auth_token,
            ip_address=client_info.get('ip_address'),
            permissions=perm_levels if perm_levels else None
        )
    
    async def handle_message(
        self,
        message: Dict[str, Any],
        client_info: Dict[str, Any],
        send_callback: Callable[[Dict[str, Any]], Any]
    ) -> None:
        """
        Handle incoming WebSocket message.
        
        Args:
            message: Parsed JSON message
            client_info: Client connection info
            send_callback: Callback to send response
        """
        try:
            # Validate message format
            if not isinstance(message, dict):
                await send_callback({
                    'success': False,
                    'error': 'Invalid message format',
                    'error_code': ERROR_CODES['INVALID_PATH']
                })
                return
            
            # Get action type
            action = message.get('action')
            if not action:
                await send_callback({
                    'success': False,
                    'error': 'Missing action field',
                    'error_code': ERROR_CODES['INVALID_PATH']
                })
                return
            
            # Get handler
            handler = self.message_handlers.get(action)
            if not handler:
                await send_callback({
                    'success': False,
                    'error': f'Unknown action: {action}',
                    'error_code': ERROR_CODES['INVALID_PATH']
                })
                return
            
            # Create security context
            context = self._create_context(message, client_info)
            
            # Handle request
            await handler(message, context, send_callback)
            
        except Exception as e:
            logger.error(f"Error handling WebSocket message: {e}")
            await send_callback({
                'success': False,
                'error': f'Internal error: {str(e)}',
                'error_code': ERROR_CODES['INTERNAL_ERROR']
            })
    
    async def _handle_list_directory(
        self,
        message: Dict[str, Any],
        context: SecurityContext,
        send: Callable[[Dict[str, Any]], Any]
    ) -> None:
        """Handle list_directory request."""
        path = message.get('path', '/')
        include_hidden = message.get('include_hidden')
        filter_pattern = message.get('filter')
        
        response = await self.file_service.list_directory(
            path=path,
            context=context,
            include_hidden=include_hidden,
            filter_pattern=filter_pattern
        )
        
        await send(response.to_dict())
    
    async def _handle_get_metadata(
        self,
        message: Dict[str, Any],
        context: SecurityContext,
        send: Callable[[Dict[str, Any]], Any]
    ) -> None:
        """Handle get_metadata request."""
        path = message.get('path')
        
        if not path:
            await send({
                'success': False,
                'error': 'Missing path field',
                'error_code': ERROR_CODES['INVALID_PATH']
            })
            return
        
        response = await self.file_service.get_file_metadata(path, context)
        await send(response.to_dict())
    
    async def _handle_download_file(
        self,
        message: Dict[str, Any],
        context: SecurityContext,
        send: Callable[[Dict[str, Any]], Any]
    ) -> None:
        """Handle download_file request."""
        path = message.get('path')
        start_byte = message.get('start_byte', 0)
        end_byte = message.get('end_byte')
        
        if not path:
            await send({
                'success': False,
                'error': 'Missing path field',
                'error_code': ERROR_CODES['INVALID_PATH']
            })
            return
        
        response = await self.file_service.download_file(
            path=path,
            context=context,
            start_byte=start_byte,
            end_byte=end_byte
        )
        
        await send(response.to_dict())
        
        # If successful, stream file content if requested
        if response.success and message.get('stream_content'):
            full_path = response.data.get('full_path')
            start = response.data.get('start_byte', 0)
            end = response.data.get('end_byte')
            
            try:
                async for chunk in self.file_service.read_file_chunks(
                    full_path, start_byte=start, end_byte=end
                ):
                    await send({
                        'type': 'file_chunk',
                        'data': chunk.hex(),  # Encode binary as hex
                        'request_id': response.request_id
                    })
                
                # Send completion
                await send({
                    'type': 'file_complete',
                    'request_id': response.request_id
                })
                
            except Exception as e:
                logger.error(f"Error streaming file: {e}")
                await send({
                    'type': 'file_error',
                    'error': str(e),
                    'request_id': response.request_id
                })
    
    async def _handle_ping(
        self,
        message: Dict[str, Any],
        context: SecurityContext,
        send: Callable[[Dict[str, Any]], Any]
    ) -> None:
        """Handle ping request."""
        await send({
            'success': True,
            'type': 'pong',
            'timestamp': datetime.utcnow().timestamp()
        })


# ============== Initialization ==============

class FileSystemAPI:
    """
    Main File System API class.
    Provides initialization and access to all components.
    """
    
    def __init__(
        self,
        root_directory: str = "/root/.openclaw/workspace/projects/",
        allow_hidden: bool = False,
        require_auth: bool = False,
        secret_key: Optional[str] = None,
        allowed_origins: Optional[List[str]] = None
    ):
        """
        Initialize the File System API.
        
        Args:
            root_directory: Root directory for file operations
            allow_hidden: Whether to allow hidden files
            require_auth: Whether authentication is required
            secret_key: Secret key for token generation
            allowed_origins: List of allowed CORS origins
        """
        self.root_directory = root_directory
        self.allow_hidden = allow_hidden
        
        # Initialize logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Initialize components
        self.validator = initialize_validator(
            root_directory=root_directory,
            allow_hidden=allow_hidden
        )
        
        self.security = initialize_security(
            secret_key=secret_key,
            require_auth=require_auth,
            allowed_origins=allowed_origins or ["*"]
        )
        
        self.file_service = FileSystemService(
            root_directory=root_directory,
            allow_hidden=allow_hidden
        )
        
        self.ws_handler = FileSystemWebSocketHandler(self.file_service)
        
        logger.info("FileSystemAPI initialized successfully")
    
    async def handle_websocket_message(
        self,
        message: Union[str, Dict[str, Any]],
        client_info: Dict[str, Any],
        send_callback: Callable[[Dict[str, Any]], Any]
    ) -> None:
        """
        Handle WebSocket message (entry point for integration).
        
        Args:
            message: Message (string JSON or parsed dict)
            client_info: Client connection information
            send_callback: Callback to send response
        """
        try:
            # Parse JSON if string
            if isinstance(message, str):
                message = json.loads(message)
            
            # Sanitize message data
            message = self.security.sanitize_request_data(message)
            
            # Handle message
            await self.ws_handler.handle_message(message, client_info, send_callback)
            
        except json.JSONDecodeError as e:
            await send_callback({
                'success': False,
                'error': f'Invalid JSON: {str(e)}',
                'error_code': ERROR_CODES['INVALID_PATH']
            })
        except Exception as e:
            logger.error(f"Error in handle_websocket_message: {e}")
            await send_callback({
                'success': False,
                'error': f'Internal error: {str(e)}',
                'error_code': ERROR_CODES['INTERNAL_ERROR']
            })
    
    def get_service(self) -> FileSystemService:
        """Get the file system service instance."""
        return self.file_service
    
    def get_validator(self) -> PathValidator:
        """Get the path validator instance."""
        return self.validator
    
    def get_security(self) -> SecurityManager:
        """Get the security manager instance."""
        return self.security


# Factory function for easy initialization
def create_file_api(
    root_directory: str = "/root/.openclaw/workspace/projects/",
    allow_hidden: bool = False,
    require_auth: bool = False,
    secret_key: Optional[str] = None
) -> FileSystemAPI:
    """
    Create and configure the File System API.
    
    Args:
        root_directory: Root directory for file operations
        allow_hidden: Whether to allow hidden files
        require_auth: Whether authentication is required
        secret_key: Secret key for authentication
        
    Returns:
        Configured FileSystemAPI instance
    """
    return FileSystemAPI(
        root_directory=root_directory,
        allow_hidden=allow_hidden,
        require_auth=require_auth,
        secret_key=secret_key
    )
