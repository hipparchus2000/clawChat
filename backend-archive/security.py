"""
ClawChat File System API - Security Module
==========================================
Provides security layer for permission checking and request validation.
"""

import asyncio
import hashlib
import hmac
import logging
import secrets
import time
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Set, Callable, Any
from functools import wraps
import json

logger = logging.getLogger(__name__)


class PermissionLevel(Enum):
    """Permission levels for file system operations."""
    NONE = 0
    READ = 1
    DOWNLOAD = 2
    LIST = 3
    WRITE = 4
    DELETE = 5
    ADMIN = 6


@dataclass
class SecurityContext:
    """Security context for a request."""
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    permissions: Set[PermissionLevel] = None
    ip_address: Optional[str] = None
    request_time: float = None
    auth_token: Optional[str] = None
    
    def __post_init__(self):
        if self.permissions is None:
            self.permissions = {PermissionLevel.READ}
        if self.request_time is None:
            self.request_time = time.time()
    
    def has_permission(self, level: PermissionLevel) -> bool:
        """Check if context has at least the specified permission level."""
        if PermissionLevel.ADMIN in self.permissions:
            return True
        return level in self.permissions
    
    def can_read(self) -> bool:
        return self.has_permission(PermissionLevel.READ)
    
    def can_download(self) -> bool:
        return self.has_permission(PermissionLevel.DOWNLOAD)
    
    def can_list(self) -> bool:
        return self.has_permission(PermissionLevel.LIST)
    
    def can_write(self) -> bool:
        return self.has_permission(PermissionLevel.WRITE)
    
    def can_delete(self) -> bool:
        return self.has_permission(PermissionLevel.DELETE)


class RateLimiter:
    """Rate limiter for API requests."""
    
    def __init__(
        self,
        max_requests: int = 100,
        window_seconds: int = 60,
        burst_size: int = 10
    ):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.burst_size = burst_size
        self._requests: Dict[str, List[float]] = {}
        self._lock = asyncio.Lock()
    
    async def is_allowed(self, key: str) -> bool:
        """Check if a request is allowed under rate limiting."""
        async with self._lock:
            now = time.time()
            
            # Clean old requests
            if key in self._requests:
                self._requests[key] = [
                    req_time for req_time in self._requests[key]
                    if now - req_time < self.window_seconds
                ]
            else:
                self._requests[key] = []
            
            # Check burst limit
            if len(self._requests[key]) >= self.burst_size:
                return False
            
            # Check rate limit
            if len(self._requests[key]) >= self.max_requests:
                return False
            
            # Record request
            self._requests[key].append(now)
            return True
    
    async def get_remaining(self, key: str) -> int:
        """Get remaining requests allowed."""
        async with self._lock:
            now = time.time()
            
            if key not in self._requests:
                return self.burst_size
            
            # Clean old requests
            self._requests[key] = [
                req_time for req_time in self._requests[key]
                if now - req_time < self.window_seconds
            ]
            
            return max(0, self.burst_size - len(self._requests[key]))


class SecurityManager:
    """
    Manages security for the file system API.
    Handles authentication, authorization, and request validation.
    """
    
    def __init__(
        self,
        secret_key: Optional[str] = None,
        token_ttl: int = 3600,
        require_auth: bool = False,
        allowed_origins: Optional[List[str]] = None
    ):
        """
        Initialize the security manager.
        
        Args:
            secret_key: Secret key for token generation
            token_ttl: Token time-to-live in seconds
            require_auth: Whether authentication is required
            allowed_origins: List of allowed CORS origins
        """
        self.secret_key = secret_key or secrets.token_hex(32)
        self.token_ttl = token_ttl
        self.require_auth = require_auth
        self.allowed_origins = allowed_origins or ["*"]
        
        # Rate limiters for different endpoints
        self.list_rate_limiter = RateLimiter(max_requests=60, window_seconds=60)
        self.download_rate_limiter = RateLimiter(max_requests=30, window_seconds=60)
        self.metadata_rate_limiter = RateLimiter(max_requests=120, window_seconds=60)
        
        # Active sessions
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._session_lock = asyncio.Lock()
        
        logger.info("SecurityManager initialized")
    
    def create_context(
        self,
        user_id: Optional[str] = None,
        auth_token: Optional[str] = None,
        ip_address: Optional[str] = None,
        permissions: Optional[List[PermissionLevel]] = None
    ) -> SecurityContext:
        """
        Create a security context for a request.
        
        Args:
            user_id: User identifier
            auth_token: Authentication token
            ip_address: Client IP address
            permissions: List of permissions
            
        Returns:
            SecurityContext instance
        """
        session_id = secrets.token_hex(16)
        
        perms = set(permissions) if permissions else {PermissionLevel.READ}
        
        # Validate token if provided
        if auth_token:
            token_data = self._verify_token(auth_token)
            if token_data:
                user_id = token_data.get('user_id', user_id)
                perms.update(token_data.get('permissions', []))
        
        context = SecurityContext(
            user_id=user_id,
            session_id=session_id,
            permissions=perms,
            ip_address=ip_address,
            auth_token=auth_token
        )
        
        return context
    
    def _generate_token(self, user_id: str, permissions: List[str]) -> str:
        """Generate an authentication token."""
        timestamp = int(time.time())
        data = f"{user_id}:{':'.join(permissions)}:{timestamp}"
        signature = hmac.new(
            self.secret_key.encode(),
            data.encode(),
            hashlib.sha256
        ).hexdigest()[:16]
        
        token_data = {
            'user_id': user_id,
            'permissions': permissions,
            'timestamp': timestamp,
            'signature': signature
        }
        
        # Base64 encode
        import base64
        return base64.urlsafe_b64encode(
            json.dumps(token_data).encode()
        ).decode().rstrip('=')
    
    def _verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify an authentication token."""
        try:
            import base64
            # Add padding if needed
            padding = 4 - len(token) % 4
            if padding != 4:
                token += '=' * padding
            
            token_data = json.loads(base64.urlsafe_b64decode(token.encode()))
            
            # Check expiration
            timestamp = token_data.get('timestamp', 0)
            if time.time() - timestamp > self.token_ttl:
                return None
            
            # Verify signature
            user_id = token_data.get('user_id', '')
            permissions = token_data.get('permissions', [])
            signature = token_data.get('signature', '')
            
            data = f"{user_id}:{':'.join(permissions)}:{timestamp}"
            expected_signature = hmac.new(
                self.secret_key.encode(),
                data.encode(),
                hashlib.sha256
            ).hexdigest()[:16]
            
            if not hmac.compare_digest(signature, expected_signature):
                return None
            
            return token_data
            
        except Exception as e:
            logger.warning(f"Token verification failed: {e}")
            return None
    
    async def check_permission(
        self,
        context: SecurityContext,
        required_level: PermissionLevel,
        operation: str = "operation"
    ) -> bool:
        """
        Check if context has required permission.
        
        Args:
            context: Security context
            required_level: Required permission level
            operation: Name of operation for logging
            
        Returns:
            True if allowed, False otherwise
        """
        if not self.require_auth:
            return True
        
        if context.has_permission(required_level):
            return True
        
        logger.warning(
            f"Permission denied for user {context.user_id} "
            f"on {operation}: requires {required_level.name}"
        )
        return False
    
    async def check_rate_limit(
        self,
        context: SecurityContext,
        rate_limiter: RateLimiter,
        operation: str = "operation"
    ) -> Tuple[bool, int]:
        """
        Check rate limit for an operation.
        
        Args:
            context: Security context
            rate_limiter: Rate limiter to use
            operation: Name of operation
            
        Returns:
            Tuple of (allowed, remaining_requests)
        """
        key = context.ip_address or context.session_id or "anonymous"
        allowed = await rate_limiter.is_allowed(key)
        remaining = await rate_limiter.get_remaining(key)
        
        if not allowed:
            logger.warning(f"Rate limit exceeded for {key} on {operation}")
        
        return allowed, remaining
    
    def validate_origin(self, origin: Optional[str]) -> bool:
        """Validate request origin for CORS."""
        if not origin:
            return True
        
        if "*" in self.allowed_origins:
            return True
        
        return origin in self.allowed_origins
    
    def sanitize_request_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize request data to prevent injection attacks."""
        sanitized = {}
        
        for key, value in data.items():
            # Sanitize keys
            clean_key = ''.join(c for c in key if c.isalnum() or c in '_-')
            
            # Sanitize string values
            if isinstance(value, str):
                # Remove null bytes
                clean_value = value.replace('\x00', '')
                # Limit length
                clean_value = clean_value[:10000]
                sanitized[clean_key] = clean_value
            elif isinstance(value, (int, float, bool)):
                sanitized[clean_key] = value
            elif isinstance(value, dict):
                sanitized[clean_key] = self.sanitize_request_data(value)
            elif isinstance(value, list):
                sanitized[clean_key] = [
                    self.sanitize_request_data(v) if isinstance(v, dict)
                    else (v[:10000] if isinstance(v, str) else v)
                    for v in value[:1000]  # Limit array size
                ]
            else:
                sanitized[clean_key] = str(value)[:1000]
        
        return sanitized
    
    def log_security_event(
        self,
        event_type: str,
        context: SecurityContext,
        details: Optional[Dict[str, Any]] = None
    ):
        """Log a security-related event."""
        log_data = {
            'event_type': event_type,
            'user_id': context.user_id,
            'session_id': context.session_id,
            'ip_address': context.ip_address,
            'timestamp': time.time()
        }
        
        if details:
            log_data['details'] = details
        
        logger.info(f"Security event: {json.dumps(log_data)}")


class SecurityError(Exception):
    """Base exception for security errors."""
    pass


class AuthenticationError(SecurityError):
    """Raised when authentication fails."""
    pass


class AuthorizationError(SecurityError):
    """Raised when authorization fails."""
    pass


class RateLimitError(SecurityError):
    """Raised when rate limit is exceeded."""
    pass


# Global security manager instance
_security_manager: Optional[SecurityManager] = None


def get_security_manager() -> SecurityManager:
    """Get the global security manager instance."""
    if _security_manager is None:
        raise RuntimeError("Security manager not initialized. Call initialize_security() first.")
    return _security_manager


def initialize_security(
    secret_key: Optional[str] = None,
    require_auth: bool = False,
    allowed_origins: Optional[List[str]] = None
) -> SecurityManager:
    """Initialize the global security manager."""
    global _security_manager
    _security_manager = SecurityManager(
        secret_key=secret_key,
        require_auth=require_auth,
        allowed_origins=allowed_origins
    )
    return _security_manager


def require_permission(level: PermissionLevel):
    """Decorator to require a specific permission level."""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract context from kwargs or first argument
            context = kwargs.get('context')
            if not context and args:
                context = args[0] if isinstance(args[0], SecurityContext) else None
            
            if not context:
                raise AuthorizationError("Security context required")
            
            security = get_security_manager()
            if not await security.check_permission(context, level, func.__name__):
                raise AuthorizationError(f"Permission denied: requires {level.name}")
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator
