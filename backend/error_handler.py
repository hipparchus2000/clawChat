"""Comprehensive Error Handling System for ClawChat.

This module provides a robust error handling framework with:
1. Error classification (user, system, security errors)
2. User-friendly error messages
3. Error recovery strategies and fallbacks
4. Structured error context
5. Integration with existing logging
"""

import json
import logging
import traceback
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union, Callable, Type
from functools import wraps

from logging_config import get_logger


class ErrorCategory(Enum):
    """Categories of errors for classification and handling."""
    USER_ERROR = "user_error"          # Client-side mistakes (validation, bad input)
    SYSTEM_ERROR = "system_error"      # Server-side issues (database, network, bugs)
    SECURITY_ERROR = "security_error"  # Authentication, authorization, attacks
    INTEGRATION_ERROR = "integration_error"  # Third-party service failures
    PERFORMANCE_ERROR = "performance_error"  # Timeouts, resource exhaustion
    CONFIGURATION_ERROR = "configuration_error"  # Misconfiguration


class ErrorSeverity(Enum):
    """Severity levels for error prioritization."""
    LOW = "low"          # Minor issues, non-critical
    MEDIUM = "medium"    # Significant issues requiring attention
    HIGH = "high"        # Critical issues affecting functionality
    CRITICAL = "critical"  # System outage or security breach


@dataclass
class ErrorContext:
    """Structured context for error reporting."""
    error_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    endpoint: Optional[str] = None
    method: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    additional_context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary for serialization."""
        return asdict(self)


class ClawChatError(Exception):
    """Base exception class for ClawChat with structured error handling."""
    
    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.SYSTEM_ERROR,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        user_message: Optional[str] = None,
        context: Optional[ErrorContext] = None,
        original_error: Optional[Exception] = None,
        recovery_strategy: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize a structured ClawChat error.
        
        Args:
            message: Internal error message for logging
            category: Error category for classification
            severity: Error severity level
            user_message: User-friendly error message (defaults to generic message)
            context: Error context with metadata
            original_error: Original exception that caused this error
            recovery_strategy: Suggested recovery strategy
            **kwargs: Additional error metadata
        """
        super().__init__(message)
        self.message = message
        self.category = category
        self.severity = severity
        self.user_message = user_message or self._get_default_user_message(category)
        self.context = context or ErrorContext()
        self.original_error = original_error
        self.recovery_strategy = recovery_strategy
        self.metadata = kwargs
        
        # Generate error ID if not in context
        if not self.context.error_id:
            self.context.error_id = str(uuid.uuid4())
        
        # Set timestamp if not already set
        if not self.context.timestamp:
            self.context.timestamp = datetime.utcnow().isoformat()
    
    def _get_default_user_message(self, category: ErrorCategory) -> str:
        """Get default user-friendly message based on error category."""
        messages = {
            ErrorCategory.USER_ERROR: "There was a problem with your request. Please check your input and try again.",
            ErrorCategory.SYSTEM_ERROR: "We're experiencing technical difficulties. Please try again later.",
            ErrorCategory.SECURITY_ERROR: "Access denied. Please check your credentials and try again.",
            ErrorCategory.INTEGRATION_ERROR: "Service temporarily unavailable. Please try again later.",
            ErrorCategory.PERFORMANCE_ERROR: "The request took too long to process. Please try again.",
            ErrorCategory.CONFIGURATION_ERROR: "System configuration error. Please contact support.",
        }
        return messages.get(category, "An unexpected error occurred. Please try again.")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for serialization."""
        return {
            "error_id": self.context.error_id,
            "timestamp": self.context.timestamp,
            "category": self.category.value,
            "severity": self.severity.value,
            "message": self.message,
            "user_message": self.user_message,
            "context": self.context.to_dict(),
            "recovery_strategy": self.recovery_strategy,
            "metadata": self.metadata,
            "traceback": traceback.format_exc() if self.original_error else None,
        }
    
    def __str__(self) -> str:
        """String representation for logging."""
        return f"[{self.category.value}] {self.message} (ID: {self.context.error_id})"


class UserError(ClawChatError):
    """Errors caused by invalid user input or actions."""
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.USER_ERROR,
            severity=ErrorSeverity.LOW,
            **kwargs
        )


class SystemError(ClawChatError):
    """Errors caused by system failures or bugs."""
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.SYSTEM_ERROR,
            severity=ErrorSeverity.HIGH,
            **kwargs
        )


class SecurityError(ClawChatError):
    """Errors related to security violations."""
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.SECURITY_ERROR,
            severity=ErrorSeverity.CRITICAL,
            **kwargs
        )


class IntegrationError(ClawChatError):
    """Errors from third-party service failures."""
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.INTEGRATION_ERROR,
            severity=ErrorSeverity.MEDIUM,
            **kwargs
        )


class PerformanceError(ClawChatError):
    """Errors related to performance issues."""
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.PERFORMANCE_ERROR,
            severity=ErrorSeverity.MEDIUM,
            **kwargs
        )


class ConfigurationError(ClawChatError):
    """Errors from misconfiguration."""
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.CONFIGURATION_ERROR,
            severity=ErrorSeverity.HIGH,
            **kwargs
        )


class ErrorHandler:
    """Main error handling orchestrator."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize error handler.
        
        Args:
            logger: Logger instance (defaults to clawchat.error_handler)
        """
        self.logger = logger or get_logger('error_handler')
        self._recovery_strategies: Dict[str, Callable] = {}
        self._alert_thresholds: Dict[ErrorSeverity, int] = {
            ErrorSeverity.CRITICAL: 1,
            ErrorSeverity.HIGH: 5,
            ErrorSeverity.MEDIUM: 10,
        }
        self._error_counts: Dict[str, int] = {}
        
    def handle_error(
        self,
        error: Exception,
        context: Optional[ErrorContext] = None,
        raise_again: bool = False
    ) -> Dict[str, Any]:
        """
        Handle an error with logging, metrics, and recovery.
        
        Args:
            error: Exception to handle
            context: Additional error context
            raise_again: Whether to re-raise the error after handling
            
        Returns:
            Error information dictionary
        """
        # Convert generic exceptions to ClawChatError if needed
        if not isinstance(error, ClawChatError):
            error = self._wrap_generic_error(error, context)
        
        # Add context if provided
        if context and isinstance(error, ClawChatError):
            error.context = context
        
        # Log the error
        self._log_error(error)
        
        # Update metrics
        self._update_error_metrics(error)
        
        # Check for alert thresholds
        self._check_alert_thresholds(error)
        
        # Attempt recovery if strategy exists
        recovery_result = self._attempt_recovery(error)
        
        # Prepare response
        error_info = error.to_dict()
        error_info["recovery_attempted"] = recovery_result is not None
        error_info["recovery_successful"] = recovery_result if recovery_result is not None else False
        
        # Re-raise if requested
        if raise_again:
            raise error
        
        return error_info
    
    def _wrap_generic_error(
        self,
        error: Exception,
        context: Optional[ErrorContext] = None
    ) -> ClawChatError:
        """Wrap generic exceptions in ClawChatError."""
        # Determine error category based on exception type
        if isinstance(error, (ValueError, TypeError, AttributeError)):
            category = ErrorCategory.USER_ERROR
            severity = ErrorSeverity.LOW
        elif isinstance(error, (IOError, OSError, ConnectionError)):
            category = ErrorCategory.SYSTEM_ERROR
            severity = ErrorSeverity.HIGH
        elif isinstance(error, (PermissionError, KeyError)):
            category = ErrorCategory.SECURITY_ERROR
            severity = ErrorSeverity.CRITICAL
        else:
            category = ErrorCategory.SYSTEM_ERROR
            severity = ErrorSeverity.MEDIUM
        
        return ClawChatError(
            message=str(error),
            category=category,
            severity=severity,
            original_error=error,
            context=context,
        )
    
    def _log_error(self, error: ClawChatError) -> None:
        """Log error with appropriate level and structured context."""
        log_methods = {
            ErrorSeverity.LOW: self.logger.warning,
            ErrorSeverity.MEDIUM: self.logger.error,
            ErrorSeverity.HIGH: self.logger.error,
            ErrorSeverity.CRITICAL: self.logger.critical,
        }
        
        log_method = log_methods.get(error.severity, self.logger.error)
        
        # Create structured log entry
        log_data = {
            "error_id": error.context.error_id,
            "category": error.category.value,
            "severity": error.severity.value,
            "message": error.message,
            "user_id": error.context.user_id,
            "session_id": error.context.session_id,
            "endpoint": error.context.endpoint,
            "method": error.context.method,
            "recovery_strategy": error.recovery_strategy,
        }
        
        log_method(f"ClawChat Error: {error}", extra={"error_data": log_data})
        
        # Log traceback for system errors
        if error.category in [ErrorCategory.SYSTEM_ERROR, ErrorCategory.CONFIGURATION_ERROR]:
            if error.original_error:
                self.logger.debug(
                    f"Original error traceback for {error.context.error_id}:",
                    exc_info=error.original_error
                )
    
    def _update_error_metrics(self, error: ClawChatError) -> None:
        """Update error metrics and counters."""
        error_key = f"{error.category.value}:{error.severity.value}"
        self._error_counts[error_key] = self._error_counts.get(error_key, 0) + 1
        
        # Also track by endpoint if available
        if error.context.endpoint:
            endpoint_key = f"endpoint:{error.context.endpoint}:{error.category.value}"
            self._error_counts[endpoint_key] = self._error_counts.get(endpoint_key, 0) + 1
    
    def _check_alert_thresholds(self, error: ClawChatError) -> None:
        """Check if error thresholds are exceeded and trigger alerts."""
        error_key = f"{error.category.value}:{error.severity.value}"
        count = self._error_counts.get(error_key, 0)
        threshold = self._alert_thresholds.get(error.severity)
        
        if threshold and count >= threshold:
            self._trigger_alert(error, count, threshold)
    
    def _trigger_alert(
        self,
        error: ClawChatError,
        count: int,
        threshold: int
    ) -> None:
        """Trigger alert for critical error conditions."""
        alert_message = (
            f"🚨 ALERT: Error threshold exceeded!\n"
            f"Error: {error.category.value} ({error.severity.value})\n"
            f"Count: {count} (threshold: {threshold})\n"
            f"Last Error ID: {error.context.error_id}\n"
            f"Message: {error.message}\n"
            f"Endpoint: {error.context.endpoint or 'N/A'}"
        )
        
        self.logger.critical(alert_message)
        
        # Here you would integrate with external alerting systems
        # e.g., send to Slack, PagerDuty, email, etc.
        # Example: self._send_slack_alert(alert_message)
    
    def _attempt_recovery(self, error: ClawChatError) -> Optional[bool]:
        """Attempt error recovery based on strategy."""
        if not error.recovery_strategy:
            return None
        
        strategy = self._recovery_strategies.get(error.recovery_strategy)
        if not strategy:
            self.logger.warning(
                f"No recovery strategy found for: {error.recovery_strategy}"
            )
            return None
        
        try:
            success = strategy(error)
            self.logger.info(
                f"Recovery strategy '{error.recovery_strategy}' "
                f"{'succeeded' if success else 'failed'} for error {error.context.error_id}"
            )
            return success
        except Exception as recovery_error:
            self.logger.error(
                f"Recovery strategy '{error.recovery_strategy}' failed with error: {recovery_error}",
                exc_info=True
            )
            return False
    
    def register_recovery_strategy(
        self,
        name: str,
        strategy: Callable[[ClawChatError], bool]
    ) -> None:
        """Register a custom recovery strategy."""
        self._recovery_strategies[name] = strategy
        self.logger.info(f"Registered recovery strategy: {name}")
    
    def get_error_metrics(self) -> Dict[str, Any]:
        """Get current error metrics."""
        return {
            "total_errors": sum(self._error_counts.values()),
            "error_counts": self._error_counts.copy(),
            "alert_thresholds": {
                severity.value: threshold
                for severity, threshold in self._alert_thresholds.items()
            },
        }
    
    def reset_metrics(self) -> None:
        """Reset error metrics (useful for testing)."""
        self._error_counts.clear()


# Global error handler instance
_error_handler = ErrorHandler()


def get_error_handler() -> ErrorHandler:
    """Get the global error handler instance."""
    return _error_handler


def error_handler(
    context: Optional[ErrorContext] = None,
    raise_again: bool = False,
    recovery_strategy: Optional[str] = None
):
    """
    Decorator for automatic error handling in functions.
    
    Args:
        context: Error context to use
        raise_again: Whether to re-raise errors
        recovery_strategy: Recovery strategy to attempt
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            handler = get_error_handler()
            try:
                return func(*args, **kwargs)
            except Exception as error:
                # Create context from function info if not provided
                error_context = context or ErrorContext(
                    endpoint=func.__name__,
                    method=func.__module__,
                )
                
                # Add recovery strategy if specified
                if recovery_strategy and isinstance(error, ClawChatError):
                    error.recovery_strategy = recovery_strategy
                
                return handler.handle_error(error, error_context, raise_again)
        return wrapper
    return decorator


def create_error_context(**kwargs) -> ErrorContext:
    """Helper function to create error context with common fields."""
    return ErrorContext(**kwargs)


# Example recovery strategies
def retry_recovery(error: ClawChatError) -> bool:
    """Simple retry recovery strategy."""
    # In a real implementation, this would implement retry logic
    # For now, just log and return False
    logger = get_logger('error_handler')
    logger.info(f"Retry recovery attempted for error: {error.context.error_id}")
    return False


def fallback_recovery(error: ClawChatError) -> bool:
    """Fallback to alternative service or method."""
    logger = get_logger('error_handler')
    logger.info(f"Fallback recovery attempted for error: {error.context.error_id}")
    return True


# Initialize global error handler with default strategies
_error_handler.register_recovery_strategy("retry", retry_recovery)
_error_handler.register_recovery_strategy("fallback", fallback_recovery)