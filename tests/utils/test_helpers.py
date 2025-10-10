"""Test helper utilities."""

import os
import shutil
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Dict, List
from unittest.mock import Mock, patch


class TestHelpers:
    """Collection of test helper functions."""

    @staticmethod
    def create_temp_directory(prefix: str = "test_") -> Path:
        """Create a temporary directory for testing."""
        temp_dir = Path(tempfile.mkdtemp(prefix=prefix))
        return temp_dir

    @staticmethod
    def cleanup_temp_directory(path: Path):
        """Clean up a temporary directory."""
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)

    @staticmethod
    def create_test_file(
        path: Path, content: str = "test content", binary: bool = False
    ):
        """Create a test file with content."""
        path.parent.mkdir(parents=True, exist_ok=True)

        if binary:
            path.write_bytes(content.encode() if isinstance(content, str) else content)
        else:
            path.write_text(content)

    @staticmethod
    def create_test_directory_structure(base_path: Path, structure: Dict[str, Any]):
        """Create a directory structure for testing."""

        def create_structure(current_structure: Dict[str, Any], current_path: Path):
            for name, content in current_structure.items():
                item_path = current_path / name
                if isinstance(content, dict):
                    item_path.mkdir(parents=True, exist_ok=True)
                    create_structure(content, item_path)
                else:
                    item_path.write_text(content)

        create_structure(structure, base_path)

    @staticmethod
    def wait_for_condition(
        condition: Callable[[], bool], timeout: float = 5.0, interval: float = 0.1
    ) -> bool:
        """Wait for a condition to be true."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if condition():
                return True
            time.sleep(interval)
        return False

    @staticmethod
    def assert_file_exists(path: Path, timeout: float = 5.0):
        """Assert that a file exists, with optional timeout."""
        if timeout > 0:
            assert TestHelpers.wait_for_condition(
                lambda: path.exists(), timeout
            ), f"File {path} did not appear within {timeout} seconds"
        else:
            assert path.exists(), f"File {path} does not exist"

    @staticmethod
    def assert_file_content(path: Path, expected_content: str, timeout: float = 5.0):
        """Assert that a file contains expected content."""
        TestHelpers.assert_file_exists(path, timeout)
        actual_content = path.read_text()
        assert (
            actual_content == expected_content
        ), (
            f"File content mismatch:\nExpected: {expected_content}\n"
            f"Actual: {actual_content}"
        )

    @staticmethod
    def assert_file_size(path: Path, expected_size: int, tolerance: int = 0):
        """Assert that a file has the expected size."""
        TestHelpers.assert_file_exists(path)
        actual_size = path.stat().st_size
        assert (
            abs(actual_size - expected_size) <= tolerance
        ), f"File size mismatch: expected {expected_size}, got {actual_size}"

    @staticmethod
    def mock_environment_variables(**env_vars):
        """Context manager for mocking environment variables."""
        return patch.dict(os.environ, env_vars)

    @staticmethod
    def mock_file_operations():
        """Context manager for mocking file operations."""
        return patch("pathlib.Path.exists", return_value=True)

    @staticmethod
    def create_mock_file_system_event(
        event_type: str, file_path: str, is_directory: bool = False
    ):
        """Create a mock file system event."""
        event = Mock()
        event.event_type = event_type
        event.src_path = file_path
        event.dest_path = file_path.replace(".md", "_moved.md")
        event.is_directory = is_directory
        return event

    @staticmethod
    def simulate_file_creation(file_path: Path, content: str = "test content"):
        """Simulate file creation for testing."""
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content)
        return file_path

    @staticmethod
    def simulate_file_modification(file_path: Path, new_content: str):
        """Simulate file modification for testing."""
        file_path.write_text(new_content)
        return file_path

    @staticmethod
    def simulate_file_deletion(file_path: Path):
        """Simulate file deletion for testing."""
        if file_path.exists():
            file_path.unlink()
        return file_path

    @staticmethod
    def get_file_timestamp(file_path: Path) -> float:
        """Get file modification timestamp."""
        return file_path.stat().st_mtime

    @staticmethod
    def set_file_timestamp(file_path: Path, timestamp: float):
        """Set file modification timestamp."""
        os.utime(file_path, (timestamp, timestamp))


class TestDataGenerator:
    """Generator for test data."""

    @staticmethod
    def generate_markdown_document(
        title: str = "Test Document", sections: int = 3
    ) -> str:
        """Generate a test markdown document."""
        content = f"# {title}\n\n"

        for i in range(sections):
            content += f"## Section {i + 1}\n\n"
            content += f"This is section {i + 1} of the test document. "
            content += (
                "It contains sample text to test the markdown processing "
                "functionality.\n\n"
            )

        content += (
            "## Code Example\n\n```python\ndef test_function():\n"
            "    return 'Hello, World!'\n```\n\n"
        )
        content += "## List Items\n\n- Item 1\n- Item 2\n- Item 3\n\n"
        content += "**Bold text** and *italic text* and `inline code`.\n"

        return content

    @staticmethod
    def generate_pdf_content(size: int = 1024) -> bytes:
        """Generate test PDF content."""
        header = b"%PDF-1.4\n"
        content = b"Test PDF content. " * (size // 20)
        return header + content

    @staticmethod
    def generate_large_text(size_mb: float = 1.0) -> str:
        """Generate large text content."""
        chunk = (
            "This is a test paragraph that will be repeated to create large content. "
            * 100
        )
        chunks_needed = int((size_mb * 1024 * 1024) / len(chunk.encode()))
        return chunk * chunks_needed

    @staticmethod
    def generate_unicode_content() -> str:
        """Generate content with various Unicode characters."""
        return """# Unicode Test Document

## Languages
- English: Hello, World!
- Chinese: 你好，世界！
- Japanese: こんにちは、世界！
- Arabic: مرحبا بالعالم!
- Russian: Привет, мир!

## Special Characters
- Quotes: "double" and 'single'
- Symbols: @#$%^&*()
- Currency: €£¥$
- Math: α + β = γ
- Emoji: 🚀📚💻

## Code with Unicode
```python
def hello_world():
    print("Hello, 世界! 🌍")
    return "Привет, мир!"
```
"""


class TestAssertions:
    """Custom test assertions."""

    @staticmethod
    def assert_config_valid(config: Any):
        """Assert that a configuration object is valid."""
        assert config is not None
        assert hasattr(config, "get")
        assert hasattr(config, "validate")
        assert config.validate() is True

    @staticmethod
    def assert_file_processed(file_path: Path, processed_files: List[Path]):
        """Assert that a file was processed."""
        assert file_path in processed_files, f"File {file_path} was not processed"

    @staticmethod
    def assert_statistics_updated(
        stats: Dict[str, Any], expected_changes: Dict[str, int]
    ):
        """Assert that statistics were updated correctly."""
        for key, expected_value in expected_changes.items():
            assert key in stats, f"Statistics key '{key}' not found"
            assert (
                stats[key] == expected_value
            ), f"Statistics '{key}': expected {expected_value}, got {stats[key]}"

    @staticmethod
    def assert_email_sent(
        mock_send_email: Mock, expected_to: str, expected_subject: str = None
    ):
        """Assert that an email was sent correctly."""
        assert mock_send_email.called, "Email was not sent"

        call_args = mock_send_email.call_args[0]
        email_msg = call_args[0]

        assert (
            email_msg["To"] == expected_to
        ), f"Email recipient mismatch: expected {expected_to}, got {email_msg['To']}"

        if expected_subject:
            assert (
                email_msg["Subject"] == expected_subject
            ), (
                f"Email subject mismatch: expected {expected_subject}, "
                f"got {email_msg['Subject']}"
            )

    @staticmethod
    def assert_backup_created(backup_path: Path, original_path: Path):
        """Assert that a backup was created correctly."""
        assert backup_path.exists(), f"Backup file {backup_path} does not exist"
        assert (
            backup_path.read_bytes() == original_path.read_bytes()
        ), "Backup content does not match original"
        assert (
            backup_path.name != original_path.name
        ), "Backup should have a different name"


class TestContextManagers:
    """Context managers for testing."""

    @staticmethod
    @contextmanager
    def temporary_directory(prefix: str = "test_"):
        """Context manager for temporary directory."""
        temp_dir = TestHelpers.create_temp_directory(prefix)
        try:
            yield temp_dir
        finally:
            TestHelpers.cleanup_temp_directory(temp_dir)

    @staticmethod
    @contextmanager
    def mock_smtp_server():
        """Context manager for mocking SMTP server."""
        with patch("smtplib.SMTP") as mock_smtp_class:
            mock_server = Mock()
            mock_smtp_class.return_value = mock_server
            yield mock_server

    @staticmethod
    @contextmanager
    def mock_weasyprint():
        """Context manager for mocking WeasyPrint."""
        with patch("weasyprint.HTML") as mock_html_class:
            mock_html = Mock()
            mock_html.write_pdf.return_value = b"Mock PDF content"
            mock_html_class.return_value = mock_html
            yield mock_html_class

    @staticmethod
    @contextmanager
    def mock_ocr_dependencies():
        """Context manager for mocking OCR dependencies."""
        with patch("pdf2image.convert_from_path") as mock_convert, patch(
            "pytesseract.image_to_string"
        ) as mock_ocr:
            mock_convert.return_value = [Mock()]
            mock_ocr.return_value = "Extracted text from OCR"
            yield mock_convert, mock_ocr

    @staticmethod
    @contextmanager
    def mock_file_system_events():
        """Context manager for mocking file system events."""
        with patch("watchdog.events.FileCreatedEvent") as mock_created, patch(
            "watchdog.events.FileModifiedEvent"
        ) as mock_modified, patch("watchdog.events.FileMovedEvent") as mock_moved:
            yield mock_created, mock_modified, mock_moved


class TestPerformanceHelpers:
    """Helpers for performance testing."""

    @staticmethod
    def measure_execution_time(func: Callable, *args, **kwargs) -> tuple:
        """Measure the execution time of a function."""
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        execution_time = end_time - start_time
        return result, execution_time

    @staticmethod
    def assert_execution_time_under(func: Callable, max_time: float, *args, **kwargs):
        """Assert that a function executes within a maximum time."""
        _, execution_time = TestPerformanceHelpers.measure_execution_time(
            func, *args, **kwargs
        )
        assert (
            execution_time <= max_time
        ), f"Function took {execution_time:.3f}s, expected <= {max_time}s"

    @staticmethod
    def benchmark_function(
        func: Callable, iterations: int = 100, *args, **kwargs
    ) -> Dict[str, float]:
        """Benchmark a function over multiple iterations."""
        times = []
        for _ in range(iterations):
            _, execution_time = TestPerformanceHelpers.measure_execution_time(
                func, *args, **kwargs
            )
            times.append(execution_time)

        return {
            "min": min(times),
            "max": max(times),
            "avg": sum(times) / len(times),
            "total": sum(times),
        }
