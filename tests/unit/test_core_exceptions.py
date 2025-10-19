"""Tests for core exception handling."""


from src.core.exceptions import (
    ConfigurationError,
    EmailServiceError,
    ErrorSeverity,
    FileProcessingError,
    KindleSyncError,
    SecretsError,
    ValidationError,
)


class TestKindleSyncError:
    """Test base exception class."""

    def test_basic_error_creation(self):
        """Test basic error creation."""
        error = KindleSyncError("Test error", ErrorSeverity.MEDIUM)
        assert str(error) == "[MEDIUM] Test error"
        assert error.severity == ErrorSeverity.MEDIUM
        assert error.recoverable is True
        assert error.retry_count == 0

    def test_error_with_context(self):
        """Test error with context."""
        context = {"file_path": "/test/file.md", "operation": "convert"}
        error = KindleSyncError("Test error", ErrorSeverity.HIGH, context=context)
        assert error.context == context

    def test_error_severity_levels(self):
        """Test all severity levels."""
        for severity in ErrorSeverity:
            error = KindleSyncError("Test", severity)
            assert error.severity == severity
            assert str(error) == f"[{severity.value.upper()}] Test"


class TestFileProcessingError:
    """Test file processing error."""

    def test_file_processing_error_creation(self):
        """Test file processing error creation."""
        error = FileProcessingError("File not found", file_path="/test/file.md")
        assert error.message == "File not found"
        assert error.context["file_path"] == "/test/file.md"
        assert error.severity == ErrorSeverity.MEDIUM

    def test_file_processing_error_custom_severity(self):
        """Test file processing error with custom severity."""
        error = FileProcessingError(
            "Critical file error",
            file_path="/test/file.md",
            severity=ErrorSeverity.CRITICAL,
        )
        assert error.severity == ErrorSeverity.CRITICAL


class TestEmailServiceError:
    """Test email service error."""

    def test_email_service_error_creation(self):
        """Test email service error creation."""
        error = EmailServiceError(
            "SMTP connection failed", email_address="test@example.com"
        )
        assert error.message == "SMTP connection failed"
        assert error.context["email_address"] == "test@example.com"
        assert error.severity == ErrorSeverity.HIGH


class TestConfigurationError:
    """Test configuration error."""

    def test_configuration_error_creation(self):
        """Test configuration error creation."""
        error = ConfigurationError("Invalid config", config_key="smtp.host")
        assert error.message == "Invalid config"
        assert error.context["config_key"] == "smtp.host"
        assert error.severity == ErrorSeverity.HIGH


class TestValidationError:
    """Test validation error."""

    def test_validation_error_creation(self):
        """Test validation error creation."""
        error = ValidationError("Invalid input", field_name="email")
        assert error.message == "Invalid input"
        assert error.context["field_name"] == "email"
        assert error.severity == ErrorSeverity.MEDIUM


class TestSecretsError:
    """Test secrets error."""

    def test_secrets_error_creation(self):
        """Test secrets error creation."""
        error = SecretsError("Decryption failed", secret_key="smtp_password")
        assert error.message == "Decryption failed"
        assert error.context["secret_key"] == "smtp_password"
        assert error.severity == ErrorSeverity.CRITICAL
