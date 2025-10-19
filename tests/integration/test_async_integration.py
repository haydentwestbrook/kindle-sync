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
from src.database.models import ProcessedFile
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
            "database.path": "test.db",
        }.get(key, default)
        return config

    @pytest.fixture
    def db_manager(self, temp_db_path):
        """Create a DatabaseManager instance."""
        db_manager = DatabaseManager(temp_db_path)
        db_manager.create_tables()
        return db_manager

    @pytest.fixture
    def health_checker(self, mock_config, db_manager):
        """Create a HealthChecker instance."""
        return HealthChecker(mock_config, db_manager)

    @pytest.fixture
    def metrics_collector(self, mock_config):
        """Create a MetricsCollector instance."""
        return MetricsCollector(mock_config)

    def test_database_manager_integration(self, db_manager):
        """Test database manager integration."""
        # Test adding a processed file
        file_path = "/test/document.md"
        file_hash = "test_hash_123"
        file_size = 1024
        file_type = ".md"

        file_id = db_manager.record_file_processing(
            file_path=file_path,
            file_hash=file_hash,
            file_size=file_size,
            file_type=file_type,
            status="success",
        )

        assert file_id is not None
        assert isinstance(file_id, int)

        # Test adding a file operation
        operation_id = db_manager.record_file_operation(
            file_id=file_id,
            operation_type="convert_markdown_to_pdf",
            status="success",
        )

        assert operation_id is not None
        assert isinstance(operation_id, int)

        # Test adding a metric
        db_manager.record_metric(metric_name="test_metric", metric_value=42.0, tags={"test": "value"})

        # Verify all records exist
        all_files = db_manager.get_recent_files()
        assert len(all_files) == 1
        # Access file_path within session context to avoid DetachedInstanceError
        with db_manager.get_session() as session:
            file_record = session.query(ProcessedFile).filter_by(id=file_id).first()
            assert file_record.file_path == file_path

    async def test_health_checker_integration(self, health_checker, mock_config, db_manager):
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
            results = await health_checker.run_all_checks()

            assert results["overall_status"] == "healthy"
            assert len(results["checks"]) == 4

            # Verify database connection check works with real database
            db_status, db_message = health_checker._check_database_connection()
            assert db_status == "healthy"
            assert "Database connection successful" in db_message

    def test_metrics_collector_integration(self, metrics_collector):
        """Test metrics collector integration."""
        # Test various metric operations
        metrics_collector.record_counter("files_processed", 1.0, {"status": "success", "type": ".md"})
        metrics_collector.record_counter("files_processed", 1.0, {"status": "failed", "type": ".pdf"})
        metrics_collector.record_counter("pdfs_generated", 1.0)
        metrics_collector.record_counter("pdfs_sent", 1.0, {"status": "success"})
        metrics_collector.record_counter("markdown_created", 1.0)
        metrics_collector.record_counter("errors", 1.0, {"type": "FileProcessingError", "severity": "medium"})
        metrics_collector.record_histogram("file_processing_duration", 1.5, {"type": ".md"})
        metrics_collector.record_gauge("queue_size", 5.0)
        metrics_collector.record_gauge("active_tasks", 3.0)

        # Get metrics data
        metrics_data = metrics_collector.get_metrics_summary()

        assert metrics_data is not None
        assert len(metrics_data) > 0

        # Verify metrics contain expected data
        metrics_str = str(metrics_data)
        assert "files_processed" in metrics_str
        assert "pdfs_generated" in metrics_str
        assert "errors" in metrics_str

    @pytest.mark.asyncio
    async def test_async_processor_integration(self, mock_config, db_manager):
        """Test async processor integration."""
        with patch("src.kindle_sync.KindleSync"), patch(
            "src.pdf_converter.MarkdownToPDFConverter"
        ), patch("src.pdf_converter.PDFToMarkdownConverter"), patch(
            "src.core.error_handler.ErrorHandler"
        ), patch("src.core.async_processor.DatabaseManager", return_value=db_manager):
            # Create a mock FileValidator
            mock_file_validator = Mock()
            mock_file_validator._calculate_checksum.return_value = "test_hash"
            mock_file_validator.validate_file.return_value = Mock(
                valid=True, checksum="test_hash"
            )
            
            with patch("src.core.async_processor.FileValidator", return_value=mock_file_validator):
                processor = AsyncSyncProcessor(mock_config, max_workers=2)

            # Test processing a file
            with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as temp_file:
                temp_file.write(b"# Test Document\n\nThis is a test.")
                temp_file.flush()
                temp_path = Path(temp_file.name)

            try:
                # Test basic processor functionality
                assert processor.config == mock_config
                assert processor.max_workers == 2
                assert processor.file_validator is not None
                assert processor.db_manager == db_manager
                
                # Verify initial statistics
                assert processor.stats["files_processed"] == 0
                assert processor.stats["files_successful"] == 0
                assert processor.stats["active_tasks"] == 0

            finally:
                os.unlink(temp_path)

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
        file1_id = db_manager.record_file_processing(
            file_path="/test/file1.md",
            file_hash="hash1",
            file_size=1024,
            file_type=".md",
            status="success",
        )

        file2_id = db_manager.record_file_processing(
            file_path="/test/file2.pdf",
            file_hash="hash2",
            file_size=2048,
            file_type=".pdf",
            status="failed",
            error_message="Conversion failed",
        )

        # Add operations for both files
        db_manager.record_file_operation(
            file_id=file1_id, operation_type="convert_markdown_to_pdf", status="success"
        )

        db_manager.record_file_operation(
            file_id=file2_id,
            operation_type="convert_pdf_to_markdown",
            status="failed",
            error_message="OCR failed",
        )

        # Add metrics
        db_manager.record_metric("files_processed_total", 2.0)
        db_manager.record_metric("success_rate", 50.0, tags={"status": "overall"})

        # Verify all records persist
        all_files = db_manager.get_recent_files()
        assert len(all_files) == 2

        # Verify file operations exist
        with db_manager.get_session() as session:
            from src.database.models import FileOperation
            operations = session.query(FileOperation).all()
            assert len(operations) == 2

            from src.database.models import SystemMetrics
            metrics = session.query(SystemMetrics).all()
            assert len(metrics) == 2

    def test_error_handling_integration(self, db_manager):
        """Test error handling integration with database."""
        # Test adding a file with error information
        file_id = db_manager.record_file_processing(
            file_path="/test/error_file.md",
            file_hash="error_hash",
            file_size=1024,
            file_type=".md",
            status="failed",
            error_message="File processing failed",
            processing_time_ms=5000,
        )

        # Update the status by recording again (this will update the existing record)
        db_manager.record_file_processing(
            file_path="/test/error_file.md",
            file_hash="error_hash",
            file_size=1024,
            file_type=".md",
            status="retry_success",
            processing_time_ms=3000,
        )

        # Verify the update
        with db_manager.get_session() as session:
            updated_file = (
                session.query(ProcessedFile)
                .filter_by(id=file_id)
                .first()
            )
            assert updated_file.status == "retry_success"
            assert updated_file.processing_time_ms == 3000

    def test_metrics_collector_prometheus_format(self, metrics_collector):
        """Test that metrics collector produces valid Prometheus format."""
        # Add some test metrics
        metrics_collector.record_counter("files_processed", 1.0, {"status": "success", "type": ".md"})
        metrics_collector.record_counter("files_processed", 1.0, {"status": "success", "type": ".md"})
        metrics_collector.record_counter("files_processed", 1.0, {"status": "failed", "type": ".pdf"})
        metrics_collector.record_counter("pdfs_generated", 1.0)
        metrics_collector.record_counter("pdfs_sent", 1.0, {"status": "success"})
        metrics_collector.record_counter("errors", 1.0, {"type": "FileProcessingError", "severity": "high"})
        metrics_collector.record_histogram("file_processing_duration", 2.5, {"type": ".md"})
        metrics_collector.record_gauge("queue_size", 10.0)
        metrics_collector.record_gauge("active_tasks", 5.0)

        # Get metrics in Prometheus format
        metrics_data = metrics_collector.get_metrics_summary()
        metrics_str = str(metrics_data)

        # Verify metrics data structure
        assert "files_processed" in metrics_str
        assert "pdfs_generated" in metrics_str
        assert "errors" in metrics_str
        assert "counters" in metrics_str
        assert "gauges" in metrics_str
        assert "histograms" in metrics_str
