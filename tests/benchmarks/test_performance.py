"""
Performance benchmark tests for Kindle Sync application.

These tests measure the performance of key operations to ensure
the application meets performance requirements.
"""

import tempfile
import time
from unittest.mock import Mock, patch

import pytest
from pathlib import Path

from src.config import Config
from src.core.async_processor import AsyncSyncProcessor
from src.kindle_sync import KindleSync
from src.security.validation import FileValidationRequest, FileValidator
from src.sync_processor import SyncProcessor


class TestPerformanceBenchmarks:
    """Performance benchmark tests."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration for testing."""
        config = Mock(spec=Config)
        config.get.side_effect = lambda key, default=None: {
            "advanced.max_file_size_mb": 50,
            "patterns.allowed_extensions": [".md", ".pdf", ".txt"],
            "patterns.allowed_mime_types": [
                "text/markdown",
                "application/pdf",
                "text/plain",
            ],
            "advanced.retry_attempts": 3,
            "database.path": "test.db",
        }.get(key, default)

        # Mock config methods
        config.get_obsidian_vault_path.return_value = Path("/tmp/test_vault")
        config.get_sync_folder_path.return_value = Path("/tmp/test_vault/sync")
        config.get_backup_folder_path.return_value = Path("/tmp/test_vault/backup")
        config.get_kindle_email.return_value = "test@kindle.com"
        config.get_smtp_config.return_value = {
            "server": "smtp.test.com",
            "port": 587,
            "username": "test@test.com",
            "password": "test_password",
        }
        config.get_sync_config.return_value = {
            "auto_convert_on_save": True,
            "auto_send_to_kindle": True,
            "backup_originals": True,
        }

        return config

    @pytest.fixture
    def temp_markdown_file(self):
        """Create a temporary markdown file for testing."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(
                "# Test Document\n\nThis is a test document for performance benchmarking.\n\n"
            )
            f.write("## Section 1\n\nSome content here.\n\n")
            f.write("## Section 2\n\nMore content here.\n\n")
            f.write("### Subsection\n\nEven more content.\n\n")
            f.write("```python\nprint('Hello, World!')\n```\n\n")
            f.write("**Bold text** and *italic text*.\n\n")
            f.write("- List item 1\n- List item 2\n- List item 3\n\n")
            f.write("1. Numbered item 1\n2. Numbered item 2\n3. Numbered item 3\n\n")
            temp_path = Path(f.name)

        yield temp_path
        temp_path.unlink(missing_ok=True)

    @pytest.fixture
    def temp_pdf_file(self):
        """Create a temporary PDF file for testing."""
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".pdf", delete=False) as f:
            # Write a minimal PDF header
            f.write(b"%PDF-1.4\n")
            f.write(b"1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n")
            f.write(b"2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n")
            f.write(
                b"3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n>>\nendobj\n"
            )
            f.write(
                b"xref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n"
            )
            f.write(b"trailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n174\n%%EOF\n")
            temp_path = Path(f.name)

        yield temp_path
        temp_path.unlink(missing_ok=True)

    def test_file_validation_performance(self, temp_markdown_file, benchmark):
        """Benchmark file validation performance."""
        validator = FileValidator()
        validation_request = FileValidationRequest(
            file_path=temp_markdown_file,
            max_size_mb=50,
            allowed_extensions=[".md", ".pdf", ".txt"],
            allowed_mime_types=["text/markdown", "application/pdf", "text/plain"],
        )

        def validate_file():
            return validator.validate_file(validation_request)

        result = benchmark(validate_file)
        assert result.valid is True

    def test_checksum_calculation_performance(self, temp_markdown_file, benchmark):
        """Benchmark checksum calculation performance."""
        validator = FileValidator()

        def calculate_checksum():
            return validator.calculate_checksum(temp_markdown_file)

        checksum = benchmark(calculate_checksum)
        assert len(checksum) == 64  # SHA-256 length

    def test_kindle_sync_initialization_performance(self, mock_config, benchmark):
        """Benchmark KindleSync initialization performance."""

        def initialize_kindle_sync():
            return KindleSync(mock_config)

        kindle_sync = benchmark(initialize_kindle_sync)
        assert kindle_sync is not None

    def test_sync_processor_initialization_performance(self, mock_config, benchmark):
        """Benchmark SyncProcessor initialization performance."""

        def initialize_sync_processor():
            return SyncProcessor(mock_config)

        processor = benchmark(initialize_sync_processor)
        assert processor is not None

    @pytest.mark.asyncio
    async def test_async_processor_initialization_performance(
        self, mock_config, benchmark
    ):
        """Benchmark AsyncSyncProcessor initialization performance."""

        def initialize_async_processor():
            with patch("src.core.async_processor.DatabaseManager"), patch(
                "src.core.async_processor.KindleSync"
            ), patch("src.core.async_processor.MarkdownToPDFConverter"), patch(
                "src.core.async_processor.PDFToMarkdownConverter"
            ), patch(
                "src.core.async_processor.FileValidator"
            ), patch(
                "src.core.async_processor.ErrorHandler"
            ):
                return AsyncSyncProcessor(mock_config, max_workers=2)

        processor = benchmark(initialize_async_processor)
        assert processor is not None

    def test_config_loading_performance(self, benchmark):
        """Benchmark configuration loading performance."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(
                """
obsidian:
  vault_path: "/tmp/test_vault"
  sync_folder: "kindle"

kindle:
  email: "test@kindle.com"
  smtp_server: "smtp.test.com"
  smtp_port: 587
  smtp_username: "test@test.com"
  smtp_password: "test_password"

advanced:
  async_workers: 3
  processing_queue_max_size: 100
  max_file_size_mb: 50
  retry_attempts: 3

database:
  path: "test.db"

monitoring:
  enabled: true
  exporter_host: "0.0.0.0"
  exporter_port: 8080
"""
            )
            config_path = f.name

        def load_config():
            return Config(config_path)

        try:
            config = benchmark(load_config)
            assert config is not None
        finally:
            Path(config_path).unlink(missing_ok=True)

    def test_file_processing_throughput(
        self, temp_markdown_file, mock_config, benchmark
    ):
        """Benchmark file processing throughput."""
        with patch("src.kindle_sync.smtplib.SMTP") as mock_smtp, patch(
            "src.pdf_converter.weasyprint.HTML"
        ) as mock_html, patch(
            "src.pdf_converter.reportlab.platypus.SimpleDocTemplate"
        ) as mock_doc:
            # Mock successful operations
            mock_smtp.return_value.__enter__.return_value.send_message.return_value = {}
            mock_html.return_value.write_pdf.return_value = b"PDF content"
            mock_doc.return_value.__enter__.return_value.build.return_value = None

            kindle_sync = KindleSync(mock_config)

            def process_file():
                return kindle_sync.send_pdf_to_kindle(temp_markdown_file)

            result = benchmark(process_file)
            assert result is True

    def test_memory_usage_stability(self, temp_markdown_file, mock_config):
        """Test memory usage stability during repeated operations."""
        import os

        import psutil

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        validator = FileValidator()
        validation_request = FileValidationRequest(
            file_path=temp_markdown_file,
            max_size_mb=50,
            allowed_extensions=[".md", ".pdf", ".txt"],
            allowed_mime_types=["text/markdown", "application/pdf", "text/plain"],
        )

        # Perform many operations
        for _ in range(1000):
            validator.validate_file(validation_request)
            validator.calculate_checksum(temp_markdown_file)

        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory

        # Memory increase should be reasonable (less than 50MB)
        assert (
            memory_increase < 50 * 1024 * 1024
        ), f"Memory usage increased by {memory_increase / 1024 / 1024:.2f}MB"

    def test_concurrent_file_validation_performance(
        self, temp_markdown_file, benchmark
    ):
        """Benchmark concurrent file validation performance."""
        import concurrent.futures

        validator = FileValidator()
        validation_request = FileValidationRequest(
            file_path=temp_markdown_file,
            max_size_mb=50,
            allowed_extensions=[".md", ".pdf", ".txt"],
            allowed_mime_types=["text/markdown", "application/pdf", "text/plain"],
        )

        def validate_concurrent():
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
                futures = [
                    executor.submit(validator.validate_file, validation_request)
                    for _ in range(10)
                ]
                results = [future.result() for future in futures]
            return results

        results = benchmark(validate_concurrent)
        assert len(results) == 10
        assert all(result.valid for result in results)

    def test_large_file_handling_performance(self, benchmark):
        """Benchmark handling of large files."""
        # Create a larger temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            # Write a 1MB file
            content = "# Large Document\n\n" + "This is a test line. " * 1000 + "\n\n"
            for i in range(1000):
                f.write(f"## Section {i}\n\n{content}\n\n")
            temp_path = Path(f.name)

        try:
            validator = FileValidator()
            validation_request = FileValidationRequest(
                file_path=temp_path,
                max_size_mb=10,  # Allow up to 10MB
                allowed_extensions=[".md", ".pdf", ".txt"],
                allowed_mime_types=["text/markdown", "application/pdf", "text/plain"],
            )

            def validate_large_file():
                return validator.validate_file(validation_request)

            result = benchmark(validate_large_file)
            assert result.valid is True
        finally:
            temp_path.unlink(missing_ok=True)

    def test_error_handling_performance(self, benchmark):
        """Benchmark error handling performance."""
        from src.core.error_handler import ErrorHandler
        from src.core.exceptions import ErrorSeverity, FileProcessingError

        error_handler = ErrorHandler()

        def handle_errors():
            for _ in range(100):
                error = FileProcessingError(
                    "Test error",
                    file_path="/test/path.md",
                    severity=ErrorSeverity.MEDIUM,
                )
                error_handler.handle_error(error, {"test": "context"})
            return error_handler.get_error_stats()

        stats = benchmark(handle_errors)
        assert stats["total_errors"] == 100
