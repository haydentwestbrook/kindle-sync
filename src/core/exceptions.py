"""Custom exception hierarchy for Kindle Sync application."""

from dataclasses import dataclass
from enum import Enum
from typing import Any


class ErrorSeverity(Enum):
    """Error severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class KindleSyncError(Exception):
    """Base exception for Kindle Sync application."""

    message: str
    severity: ErrorSeverity
    context: dict[str, Any] | None = None
    recoverable: bool = True
    retry_count: int = 0

    def __str__(self) -> str:
        return f"[{self.severity.value.upper()}] {self.message}"


class FileProcessingError(KindleSyncError):
    """Error during file processing."""

    def __init__(
        self,
        message: str,
        file_path: str | None = None,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        **kwargs: Any,
    ):
        context = kwargs.get("context", {})
        if file_path:
            context["file_path"] = file_path
        super().__init__(message, severity, context, **kwargs)


class EmailServiceError(KindleSyncError):
    """Error with email service."""

    def __init__(
        self,
        message: str,
        email_address: str | None = None,
        severity: ErrorSeverity = ErrorSeverity.HIGH,
        **kwargs: Any,
    ):
        context = kwargs.get("context", {})
        if email_address:
            context["email_address"] = email_address
        super().__init__(message, severity, context, **kwargs)


class ConfigurationError(KindleSyncError):
    """Configuration-related error."""

    def __init__(
        self,
        message: str,
        config_key: str | None = None,
        severity: ErrorSeverity = ErrorSeverity.HIGH,
        **kwargs: Any,
    ):
        context = kwargs.get("context", {})
        if config_key:
            context["config_key"] = config_key
        super().__init__(message, severity, context, **kwargs)


class ValidationError(KindleSyncError):
    """Input validation error."""

    def __init__(
        self,
        message: str,
        field_name: str | None = None,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        **kwargs: Any,
    ):
        context = kwargs.get("context", {})
        if field_name:
            context["field_name"] = field_name
        super().__init__(message, severity, context, **kwargs)


class SecretsError(KindleSyncError):
    """Secrets management error."""

    def __init__(
        self,
        message: str,
        secret_key: str | None = None,
        severity: ErrorSeverity = ErrorSeverity.CRITICAL,
        **kwargs: Any,
    ):
        context = kwargs.get("context", {})
        if secret_key:
            context["secret_key"] = secret_key
        super().__init__(message, severity, context, **kwargs)
