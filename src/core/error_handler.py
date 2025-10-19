"""Centralized error handling and recovery system."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger

from .exceptions import (
    ConfigurationError,
    EmailServiceError,
    ErrorSeverity,
    FileProcessingError,
    KindleSyncError,
)


class ErrorHandler:
    """Centralized error handling and recovery."""

    def __init__(self):
        self.error_stats = {
            "total_errors": 0,
            "recoverable_errors": 0,
            "critical_errors": 0,
            "errors_by_type": {},
            "errors_by_severity": {},
            "recent_errors": [],
        }
        self.max_recent_errors = 100

    def handle_error(
        self, error: KindleSyncError, context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Handle error with appropriate recovery strategy.

        Args:
            error: The error to handle
            context: Additional context information

        Returns:
            True if error was handled successfully, False otherwise
        """
        if context is None:
            context = {}

        # Update statistics
        self._update_error_stats(error)

        # Log the error
        self._log_error(error, context)

        # Attempt recovery based on error type and severity
        if error.severity == ErrorSeverity.CRITICAL:
            self.error_stats["critical_errors"] += 1
            logger.critical(f"Critical error: {error}")
            return False

        if error.recoverable:
            self.error_stats["recoverable_errors"] += 1
            logger.warning(f"Recoverable error: {error}")
            return self._attempt_recovery(error, context)

        logger.error(f"Non-recoverable error: {error}")
        return False

    def _update_error_stats(self, error: KindleSyncError) -> None:
        """Update error statistics."""
        self.error_stats["total_errors"] += 1

        # Count by error type
        error_type = type(error).__name__
        self.error_stats["errors_by_type"][error_type] = (
            self.error_stats["errors_by_type"].get(error_type, 0) + 1
        )

        # Count by severity
        severity = error.severity.value
        self.error_stats["errors_by_severity"][severity] = (
            self.error_stats["errors_by_severity"].get(severity, 0) + 1
        )

        # Add to recent errors
        error_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": error_type,
            "severity": severity,
            "message": str(error),
            "context": error.context,
        }

        self.error_stats["recent_errors"].append(error_record)

        # Keep only recent errors
        if len(self.error_stats["recent_errors"]) > self.max_recent_errors:
            self.error_stats["recent_errors"] = self.error_stats["recent_errors"][
                -self.max_recent_errors :
            ]

    def _log_error(self, error: KindleSyncError, context: Dict[str, Any]) -> None:
        """Log error with appropriate level."""
        log_message = f"Error: {error}"
        if context:
            log_message += f" | Context: {context}"
        if error.context:
            log_message += f" | Error Context: {error.context}"

        if error.severity == ErrorSeverity.CRITICAL:
            logger.critical(log_message)
        elif error.severity == ErrorSeverity.HIGH:
            logger.error(log_message)
        elif error.severity == ErrorSeverity.MEDIUM:
            logger.warning(log_message)
        else:
            logger.info(log_message)

    def _attempt_recovery(
        self, error: KindleSyncError, context: Dict[str, Any]
    ) -> bool:
        """
        Attempt to recover from an error.

        Args:
            error: The error to recover from
            context: Additional context information

        Returns:
            True if recovery was successful, False otherwise
        """
        try:
            if isinstance(error, EmailServiceError):
                return self._recover_email_service(error, context)
            elif isinstance(error, FileProcessingError):
                return self._recover_file_processing(error, context)
            elif isinstance(error, ConfigurationError):
                return self._recover_configuration(error, context)
            else:
                logger.warning(
                    f"No recovery strategy for error type: {type(error).__name__}"
                )
                return False
        except Exception as recovery_error:
            logger.error(f"Recovery attempt failed: {recovery_error}")
            return False

    def _recover_email_service(
        self, error: EmailServiceError, context: Dict[str, Any]
    ) -> bool:
        """Recover from email service errors."""
        logger.info("Attempting email service recovery...")

        # Common recovery strategies for email service
        recovery_strategies = [
            self._retry_email_connection,
            self._fallback_email_service,
            self._queue_email_for_later,
        ]

        for strategy in recovery_strategies:
            try:
                if strategy(error, context):
                    logger.info("Email service recovery successful")
                    return True
            except Exception as e:
                logger.warning(f"Recovery strategy {strategy.__name__} failed: {e}")
                continue

        logger.error("All email service recovery strategies failed")
        return False

    def _recover_file_processing(
        self, error: FileProcessingError, context: Dict[str, Any]
    ) -> bool:
        """Recover from file processing errors."""
        logger.info("Attempting file processing recovery...")

        # Common recovery strategies for file processing
        recovery_strategies = [
            self._retry_file_operation,
            self._skip_corrupted_file,
            self._backup_and_retry,
        ]

        for strategy in recovery_strategies:
            try:
                if strategy(error, context):
                    logger.info("File processing recovery successful")
                    return True
            except Exception as e:
                logger.warning(f"Recovery strategy {strategy.__name__} failed: {e}")
                continue

        logger.error("All file processing recovery strategies failed")
        return False

    def _recover_configuration(
        self, error: ConfigurationError, context: Dict[str, Any]
    ) -> bool:
        """Recover from configuration errors."""
        logger.info("Attempting configuration recovery...")

        # Configuration recovery strategies
        recovery_strategies = [
            self._use_default_config,
            self._reload_configuration,
            self._validate_and_fix_config,
        ]

        for strategy in recovery_strategies:
            try:
                if strategy(error, context):
                    logger.info("Configuration recovery successful")
                    return True
            except Exception as e:
                logger.warning(f"Recovery strategy {strategy.__name__} failed: {e}")
                continue

        logger.error("All configuration recovery strategies failed")
        return False

    # Recovery strategy implementations
    def _retry_email_connection(
        self, error: EmailServiceError, context: Dict[str, Any]
    ) -> bool:
        """Retry email connection."""
        # Implementation would retry SMTP connection
        logger.info("Retrying email connection...")
        return True  # Placeholder

    def _fallback_email_service(
        self, error: EmailServiceError, context: Dict[str, Any]
    ) -> bool:
        """Use fallback email service."""
        logger.info("Using fallback email service...")
        return False  # No fallback implemented yet

    def _queue_email_for_later(
        self, error: EmailServiceError, context: Dict[str, Any]
    ) -> bool:
        """Queue email for later processing."""
        logger.info("Queueing email for later processing...")
        return True  # Placeholder - would implement email queue

    def _retry_file_operation(
        self, error: FileProcessingError, context: Dict[str, Any]
    ) -> bool:
        """Retry file operation."""
        logger.info("Retrying file operation...")
        return True  # Placeholder

    def _skip_corrupted_file(
        self, error: FileProcessingError, context: Dict[str, Any]
    ) -> bool:
        """Skip corrupted file and continue."""
        logger.info("Skipping corrupted file...")
        return True  # Placeholder

    def _backup_and_retry(
        self, error: FileProcessingError, context: Dict[str, Any]
    ) -> bool:
        """Backup file and retry operation."""
        logger.info("Backing up file and retrying...")
        return True  # Placeholder

    def _use_default_config(
        self, error: ConfigurationError, context: Dict[str, Any]
    ) -> bool:
        """Use default configuration values."""
        logger.info("Using default configuration values...")
        return True  # Placeholder

    def _reload_configuration(
        self, error: ConfigurationError, context: Dict[str, Any]
    ) -> bool:
        """Reload configuration from file."""
        logger.info("Reloading configuration...")
        return True  # Placeholder

    def _validate_and_fix_config(
        self, error: ConfigurationError, context: Dict[str, Any]
    ) -> bool:
        """Validate and fix configuration issues."""
        logger.info("Validating and fixing configuration...")
        return True  # Placeholder

    def get_error_stats(self) -> Dict[str, Any]:
        """Get current error statistics."""
        return self.error_stats.copy()

    def get_recent_errors(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent errors."""
        return self.error_stats["recent_errors"][-limit:]

    def reset_stats(self) -> None:
        """Reset error statistics."""
        self.error_stats = {
            "total_errors": 0,
            "recoverable_errors": 0,
            "critical_errors": 0,
            "errors_by_type": {},
            "errors_by_severity": {},
            "recent_errors": [],
        }
        logger.info("Error statistics reset")
