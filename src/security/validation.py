"""Input validation and sanitization system."""

import hashlib
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union

from loguru import logger
from pathlib import Path

from ..core.exceptions import ErrorSeverity, ValidationError

# Try to import magic, fallback to None if not available
try:
    import magic
except ImportError:
    magic = None

# Try to import pydantic, fallback to basic validation if not available
try:
    from pydantic import BaseModel, Field, validator
except ImportError:
    # Fallback to basic class if pydantic is not available
    class BaseModel:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

    def validator(field_name):
        def decorator(func):
            return func

        return decorator

    def Field(default=None, **kwargs):
        return default


@dataclass
class ValidationResult:
    """Result of file validation."""

    valid: bool
    file_path: Optional[Path] = None
    error: Optional[str] = None
    checksum: Optional[str] = None
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    warnings: List[str] = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


class FileValidationRequest:
    """Request for file validation."""

    def __init__(
        self,
        file_path: Path,
        max_size_mb: int = 50,
        allowed_extensions: List[str] = None,
        allowed_mime_types: List[str] = None,
        require_checksum: bool = True,
        check_security: bool = True,
    ):
        self.file_path = file_path
        self.max_size_mb = max_size_mb
        self.allowed_extensions = allowed_extensions or [".md", ".pdf", ".txt"]
        self.allowed_mime_types = allowed_mime_types or [
            "text/markdown",
            "application/pdf",
            "text/plain",
        ]
        self.require_checksum = require_checksum
        self.check_security = check_security

        # Validate the request
        self._validate()

    def _validate(self):
        """Validate the request parameters."""
        if not self.file_path.exists():
            raise ValueError("File does not exist")
        if not self.file_path.is_file():
            raise ValueError("Path is not a file")

        # Check file size
        max_size_bytes = self.max_size_mb * 1024 * 1024
        if self.file_path.stat().st_size > max_size_bytes:
            raise ValueError(f"File size exceeds {self.max_size_mb}MB limit")

        # Check file extension
        if self.file_path.suffix.lower() not in self.allowed_extensions:
            raise ValueError(f"File extension {self.file_path.suffix} not allowed")


class FileValidator:
    """Comprehensive file validation."""

    def __init__(self):
        if magic is not None:
            try:
                self.mime_detector = magic.Magic(mime=True)
            except Exception as e:
                logger.warning(f"Failed to initialize MIME detector: {e}")
                self.mime_detector = None
        else:
            self.mime_detector = None

    def validate_file(self, request: FileValidationRequest) -> ValidationResult:
        """
        Validate file against all criteria.

        Args:
            request: Validation request with criteria

        Returns:
            Validation result with details
        """
        file_path = request.file_path
        warnings = []

        try:
            # Basic file information
            file_size = file_path.stat().st_size
            checksum = None

            if request.require_checksum:
                checksum = self._calculate_checksum(file_path)

            # MIME type validation
            mime_type = self._get_mime_type(file_path)

            # Content validation (do this first to catch corrupted files)
            content_valid, content_warnings = self._validate_content(
                file_path, mime_type
            )
            warnings.extend(content_warnings)

            if not content_valid:
                return ValidationResult(
                    valid=False,
                    file_path=file_path,
                    error="File content validation failed",
                    file_size=file_size,
                    mime_type=mime_type,
                    checksum=checksum,
                )

            # MIME type validation (after content validation)
            # For files with known extensions, be more lenient with MIME type validation
            extension = file_path.suffix.lower()
            if extension in [".md", ".pdf", ".txt"]:
                # For known extensions, use extension-based MIME type
                expected_mime_type = self._get_mime_type_from_extension(file_path)
                if expected_mime_type not in request.allowed_mime_types:
                    return ValidationResult(
                        valid=False,
                        file_path=file_path,
                        error=f"MIME type {expected_mime_type} not allowed",
                        file_size=file_size,
                        mime_type=expected_mime_type,
                    )
            else:
                # For unknown extensions, validate the detected MIME type
                if mime_type not in request.allowed_mime_types:
                    return ValidationResult(
                        valid=False,
                        file_path=file_path,
                        error=f"MIME type {mime_type} not allowed",
                        file_size=file_size,
                        mime_type=mime_type,
                    )

            # Security validation
            if request.check_security:
                security_valid, security_warnings = self._validate_security(file_path)
                warnings.extend(security_warnings)

                if not security_valid:
                    return ValidationResult(
                        valid=False,
                        file_path=file_path,
                        error="File failed security validation",
                        file_size=file_size,
                        mime_type=mime_type,
                        checksum=checksum,
                    )

            return ValidationResult(
                valid=True,
                file_path=file_path,
                file_size=file_size,
                mime_type=mime_type,
                checksum=checksum,
                warnings=warnings,
            )

        except Exception as e:
            return ValidationResult(
                valid=False, file_path=file_path, error=f"Validation error: {e}"
            )

    def _get_mime_type(self, file_path: Path) -> str:
        """Get MIME type of file."""
        try:
            # Check if file is empty
            if file_path.stat().st_size == 0:
                # For empty files, use extension-based detection
                return self._get_mime_type_from_extension(file_path)

            # For known file types, use extension-based detection first
            extension = file_path.suffix.lower()
            if extension in [".md", ".pdf", ".txt"]:
                return self._get_mime_type_from_extension(file_path)

            # For other files, try magic library
            if self.mime_detector:
                return self.mime_detector.from_file(str(file_path))
            else:
                # Fallback to file extension
                return self._get_mime_type_from_extension(file_path)
        except Exception:
            return "application/octet-stream"

    def _get_mime_type_from_extension(self, file_path: Path) -> str:
        """Get MIME type from file extension (fallback)."""
        extension_map = {
            ".md": "text/markdown",
            ".pdf": "application/pdf",
            ".txt": "text/plain",
            ".html": "text/html",
            ".json": "application/json",
            ".yaml": "application/x-yaml",
            ".yml": "application/x-yaml",
        }
        return extension_map.get(file_path.suffix.lower(), "application/octet-stream")

    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA-256 checksum of file."""
        hash_sha256 = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception as e:
            raise ValidationError(f"Failed to calculate checksum: {e}")

    def _validate_content(
        self, file_path: Path, mime_type: str
    ) -> tuple[bool, List[str]]:
        """
        Validate file content integrity.

        Returns:
            Tuple of (is_valid, warnings)
        """
        warnings = []

        try:
            if mime_type == "application/pdf":
                return self._validate_pdf_content(file_path)
            elif mime_type == "text/markdown":
                return self._validate_markdown_content(file_path)
            elif mime_type == "text/plain":
                return self._validate_text_content(file_path)
            else:
                # For unknown types, just check if file is readable
                with open(file_path, "rb") as f:
                    f.read(1024)  # Read first 1KB
                return True, warnings

        except Exception as e:
            return False, [f"Content validation failed: {e}"]

    def _validate_pdf_content(self, file_path: Path) -> tuple[bool, List[str]]:
        """Validate PDF content."""
        warnings = []

        try:
            # Try to read PDF header
            with open(file_path, "rb") as f:
                header = f.read(8)
                if not header.startswith(b"%PDF-"):
                    return False, ["Invalid PDF header"]

            # Check for common PDF issues
            with open(file_path, "rb") as f:
                content = f.read(1024)
                if b"%%EOF" not in content:
                    warnings.append(
                        "PDF may be incomplete (no EOF marker in first 1KB)"
                    )

            return True, warnings

        except Exception as e:
            return False, [f"PDF validation failed: {e}"]

    def _validate_markdown_content(self, file_path: Path) -> tuple[bool, List[str]]:
        """Validate Markdown content."""
        warnings = []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

                # Check for common Markdown issues
                if len(content.strip()) == 0:
                    warnings.append("Markdown file is empty")

                # Check for potential encoding issues
                if "\ufffd" in content:
                    warnings.append("File may contain encoding issues")

                # Check for very long lines (potential issues)
                lines = content.split("\n")
                long_lines = [i for i, line in enumerate(lines) if len(line) > 1000]
                if long_lines:
                    warnings.append(f"File contains {len(long_lines)} very long lines")

            return True, warnings

        except UnicodeDecodeError:
            return False, ["File is not valid UTF-8 text"]
        except Exception as e:
            return False, [f"Markdown validation failed: {e}"]

    def _validate_text_content(self, file_path: Path) -> tuple[bool, List[str]]:
        """Validate plain text content."""
        warnings = []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

                if len(content.strip()) == 0:
                    warnings.append("Text file is empty")

            return True, warnings

        except UnicodeDecodeError:
            return False, ["File is not valid UTF-8 text"]
        except Exception as e:
            return False, [f"Text validation failed: {e}"]

    def _validate_security(self, file_path: Path) -> tuple[bool, List[str]]:
        """
        Basic security validation.

        Returns:
            Tuple of (is_valid, warnings)
        """
        warnings = []

        try:
            with open(file_path, "rb") as f:
                content = f.read(1024)  # Read first 1KB

                # Check for executable signatures
                executable_signatures = [
                    b"\x4d\x5a",  # PE (Windows)
                    b"\x7f\x45\x4c\x46",  # ELF (Linux)
                    b"\xfe\xed\xfa",  # Mach-O (macOS)
                    b"\xce\xfa\xed\xfe",  # Mach-O (macOS)
                ]

                for sig in executable_signatures:
                    if content.startswith(sig):
                        return False, ["File appears to be an executable"]

                # Check for suspicious patterns
                suspicious_patterns = [
                    b"<script",
                    b"javascript:",
                    b"eval(",
                    b"exec(",
                    b"system(",
                ]

                for pattern in suspicious_patterns:
                    if pattern in content.lower():
                        warnings.append(
                            f"Suspicious pattern detected: {pattern.decode('utf-8', errors='ignore')}"
                        )

                # Check for embedded null bytes (potential security issue)
                if b"\x00" in content:
                    warnings.append("File contains null bytes")

            return True, warnings

        except Exception as e:
            return False, [f"Security validation failed: {e}"]

    def validate_file_path(self, file_path: Union[str, Path]) -> bool:
        """
        Validate file path for security.

        Args:
            file_path: Path to validate

        Returns:
            True if path is safe, False otherwise
        """
        try:
            path_str = str(file_path)

            # Check for path traversal attempts in the original string
            suspicious_patterns = ["..", "~", "$", "`"]

            for pattern in suspicious_patterns:
                if pattern in path_str:
                    return False

            # Check if path is within allowed directories
            # This would be configured based on application needs
            return True

        except Exception:
            return False

    def sanitize_filename(self, filename: str) -> str:
        """
        Sanitize filename for safe storage.

        Args:
            filename: Original filename

        Returns:
            Sanitized filename
        """
        import re

        # Remove or replace dangerous characters
        sanitized = re.sub(r'[<>:"/\\|?*]', "_", filename)

        # Remove leading/trailing dots and spaces
        sanitized = sanitized.strip(". ")

        # Limit length
        if len(sanitized) > 255:
            name, ext = os.path.splitext(sanitized)
            sanitized = name[: 255 - len(ext)] + ext

        # Ensure it's not empty
        if not sanitized:
            sanitized = "unnamed_file"

        return sanitized
