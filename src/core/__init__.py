"""Core modules for Kindle Sync application."""

from .exceptions import (
    KindleSyncError,
    FileProcessingError,
    EmailServiceError,
    ConfigurationError,
    ValidationError,
    ErrorSeverity,
)
from .retry import with_retry
from .error_handler import ErrorHandler

__all__ = [
    "KindleSyncError",
    "FileProcessingError", 
    "EmailServiceError",
    "ConfigurationError",
    "ValidationError",
    "ErrorSeverity",
    "with_retry",
    "ErrorHandler",
]
