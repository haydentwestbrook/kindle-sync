"""
Integration tests for async functionality.

Tests the integration of async components with the existing system.
"""

import asyncio
import os
import tempfile
from unittest.mock import AsyncMock, Mock, patch

import pytest
from pathlib import Path

from src.config import Config
from src.core.async_processor import AsyncSyncProcessor
from src.database.manager import DatabaseManager
from src.monitoring.health_checks import HealthChecker
from src.monitoring.metrics import MetricsCollector


class TestAsyncIntegration:
    """Integration tests for async functionality."""

    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database file path."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp_file:
            temp_path = Path(temp_file.name)
        yield temp_path
        # Clean up
        if temp_path.exists():
            temp_path.unlink()

    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration."""
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
            "advanced.async_workers": 2,
            "obsidian.watch_subfolders": True,
        }.get(key, default)
        return config

    @pytest.fixture
    def db_manager(self, temp_db_path):
        """Create a DatabaseManager instance."""
        return DatabaseManager(temp_db_path)

    @pytest.fixture
    def health_checker(self, mock_config, db_manager):
        """Create a HealthChecker instance."""
        return HealthChecker(mock_config, db_manager)

    @pytest.fixture
    def metrics_collector(self):
        """Create a MetricsCollector instance."""
        return MetricsCollector()

    def test_database_manager_integration(self, db_manager):
        """Test database manager integration."""
        # Test adding a processed file
        file_path = Path("/test/document.md")
        file_hash = "test_hash_123"
        file_size = 1024
        file_type = ".md"

        processed_file = db_manager.add_processed_file(
            file_path=file_path,
            file_hash=file_hash,
            file_size=file_size,
            file_type=file_type,
            status="success",
        )

        assert processed_file is not None
        assert processed_file.id is not None

        # Test adding a file operation
        file_operation = db_manager.add_file_operation(
            file_id=processed_file.id,
            operation_type="convert_markdown_to_pdf",
            status="success",
        )

        assert file_operation is not None
        assert file_operation.file_id == processed_file.id

        # Test adding a metric
        db_manager.add_metric(name="test_metric", value=42.0, labels={"test": "value"})

        # Verify all records exist
        all_files = db_manager.get_all_processed_files()
        assert len(all_files) == 1
        assert all_files[0].file_path == str(file_path)

    def test_health_checker_integration(self, health_checker, mock_config, db_manager):
        """Test health checker integration."""
        # Mock successful health checks
        with patch.object(
            health_checker, "_check_config_paths", return_value=("healthy", "Paths OK")
        ), patch.object(
            health_checker,
            "_check_database_connection",
            return_value=("healthy", "DB OK"),
        ), patch.object(
            health_checker,
            "_check_email_service_config",
            return_value=("healthy", "Email OK"),
        ), patch.object(
            health_checker,
            "_check_temp_directory_access",
            return_value=("healthy", "Temp OK"),
        ):
            results = health_checker.run_all_checks()

            assert results["overall_status"] == "healthy"
            assert len(results["checks"]) == 4

            # Verify database connection check works with real database
            db_status, db_message = health_checker._check_database_connection()
            assert db_status == "healthy"
            assert "Database connection successful" in db_message

    def test_metrics_collector_integration(self, metrics_collector):
        """Test metrics collector integration."""
        # Test various metric operations
        metrics_collector.increment_files_processed("success", ".md")
        metrics_collector.increment_files_processed("failed", ".pdf")
        metrics_collector.increment_pdfs_generated()
        metrics_collector.increment_pdfs_sent("success")
        metrics_collector.increment_markdown_created()
        metrics_collector.increment_errors("FileProcessingError", "medium")
        metrics_collector.observe_file_processing_duration(1.5, ".md")
        metrics_collector.set_queue_size(5)
        metrics_collector.set_active_tasks(3)

        # Get metrics data
        metrics_data = metrics_collector.get_latest_metrics()

        assert metrics_data is not None
        assert len(metrics_data) > 0

        # Verify metrics contain expected data
        metrics_str = metrics_data.decode("utf-8")
        assert "kindle_sync_files_processed_total" in metrics_str
        assert "kindle_sync_pdfs_generated_total" in metrics_str
        assert "kindle_sync_errors_total" in metrics_str

    @pytest.mark.asyncio
    async def test_async_processor_integration(self, mock_config, db_manager):
        """Test async processor integration."""
        with patch("src.core.async_processor.KindleSync"), patch(
            "src.core.async_processor.MarkdownToPDFConverter"
        ), patch("src.core.async_processor.PDFToMarkdownConverter"), patch(
            "src.core.async_processor.FileValidator"
        ), patch(
            "src.core.async_processor.ErrorHandler"
        ):
            processor = AsyncSyncProcessor(mock_config, db_manager, max_workers=2)

            # Test processing a file
            with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as temp_file:
                temp_file.write(b"# Test Document\n\nThis is a test.")
                temp_file.flush()
                temp_path = Path(temp_file.name)

            try:
                # Mock file validation and processing
                processor.file_validator.calculate_checksum.return_value = "test_hash"
                processor.file_validator.validate_file.return_value = Mock(
                    valid=True, checksum="test_hash"
                )
                processor.markdown_to_pdf.convert_markdown_to_pdf.return_value = (
                    temp_path.with_suffix(".pdf")
                )
                processor._send_pdf_to_kindle_async = AsyncMock(return_value=True)

                result = await processor.process_file_async(temp_path)

                assert result.success is True
                assert result.file_path == temp_path
                assert result.file_hash == "test_hash"

                # Verify database record was created
                all_files = db_manager.get_all_processed_files()
                assert len(all_files) == 1
                assert all_files[0].file_path == str(temp_path)
                assert all_files[0].status == "success"

            finally:
                os.unlink(temp_path)

            # Test shutdown
            processor.shutdown()

    def test_config_integration_with_async_settings(self, mock_config):
        """Test configuration integration with async settings."""
        # Test async-specific configuration values
        async_workers = mock_config.get("advanced.async_workers", 3)
        assert async_workers == 2  # From fixture

        max_file_size = mock_config.get("advanced.max_file_size_mb", 50)
        assert max_file_size == 50

        retry_attempts = mock_config.get("advanced.retry_attempts", 3)
        assert retry_attempts == 3

    def test_database_persistence(self, db_manager):
        """Test database persistence across operations."""
        # Add multiple records
        file1 = db_manager.add_processed_file(
            file_path=Path("/test/file1.md"),
            file_hash="hash1",
            file_size=1024,
            file_type=".md",
            status="success",
        )

        file2 = db_manager.add_processed_file(
            file_path=Path("/test/file2.pdf"),
            file_hash="hash2",
            file_size=2048,
            file_type=".pdf",
            status="failed",
            error_message="Conversion failed",
        )

        # Add operations for both files
        db_manager.add_file_operation(
            file_id=file1.id, operation_type="convert_markdown_to_pdf", status="success"
        )

        db_manager.add_file_operation(
            file_id=file2.id,
            operation_type="convert_pdf_to_markdown",
            status="failed",
            details="OCR failed",
        )

        # Add metrics
        db_manager.add_metric("files_processed_total", 2.0)
        db_manager.add_metric("success_rate", 50.0, {"status": "overall"})

        # Verify all records persist
        all_files = db_manager.get_all_processed_files()
        assert len(all_files) == 2

        # Verify file operations exist
        with db_manager.get_session() as session:
            operations = session.query(db_manager.FileOperation).all()
            assert len(operations) == 2

            metrics = session.query(db_manager.Metric).all()
            assert len(metrics) == 2

    def test_error_handling_integration(self, db_manager):
        """Test error handling integration with database."""
        # Test adding a file with error information
        processed_file = db_manager.add_processed_file(
            file_path=Path("/test/error_file.md"),
            file_hash="error_hash",
            file_size=1024,
            file_type=".md",
            status="failed",
            error_message="File processing failed",
            processing_time_ms=5000,
        )

        # Update the status
        db_manager.update_processed_file_status(
            file_id=processed_file.id, status="retry_success", processing_time_ms=3000
        )

        # Verify the update
        with db_manager.get_session() as session:
            updated_file = (
                session.query(db_manager.ProcessedFile)
                .filter_by(id=processed_file.id)
                .first()
            )
            assert updated_file.status == "retry_success"
            assert updated_file.processing_time_ms == 3000

    def test_metrics_collector_prometheus_format(self, metrics_collector):
        """Test that metrics collector produces valid Prometheus format."""
        # Add some test metrics
        metrics_collector.increment_files_processed("success", ".md")
        metrics_collector.increment_files_processed("success", ".md")
        metrics_collector.increment_files_processed("failed", ".pdf")
        metrics_collector.increment_pdfs_generated()
        metrics_collector.increment_pdfs_sent("success")
        metrics_collector.increment_errors("FileProcessingError", "high")
        metrics_collector.observe_file_processing_duration(2.5, ".md")
        metrics_collector.set_queue_size(10)
        metrics_collector.set_active_tasks(5)

        # Get metrics in Prometheus format
        metrics_data = metrics_collector.get_latest_metrics()
        metrics_str = metrics_data.decode("utf-8")

        # Verify Prometheus format
        assert "# HELP" in metrics_str
        assert "# TYPE" in metrics_str
        assert (
            'kindle_sync_files_processed_total{status="success",file_type=".md"} 2.0'
            in metrics_str
        )
        assert (
            'kindle_sync_files_processed_total{status="failed",file_type=".pdf"} 1.0'
            in metrics_str
        )
        assert "kindle_sync_pdfs_generated_total 1.0" in metrics_str
        assert (
            'kindle_sync_errors_total{error_type="FileProcessingError",severity="high"} 1.0'
            in metrics_str
        )
        assert "kindle_sync_processing_queue_size 10.0" in metrics_str
        assert "kindle_sync_active_processing_tasks 5.0" in metrics_str
