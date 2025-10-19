"""
Unit tests for DatabaseManager.

Tests the database connection and operations management.
"""

import tempfile
from unittest.mock import Mock, patch

import pytest
from pathlib import Path
from sqlalchemy.exc import SQLAlchemyError

from src.core.exceptions import ErrorSeverity, KindleSyncError
from src.database.manager import DatabaseManager
from src.database.models import (
    FileOperation,
    ProcessedFile,
    SystemMetrics,
    ProcessingStatus,
)


class TestDatabaseManager:
    """Test cases for DatabaseManager."""

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
    def db_manager(self, temp_db_path):
        """Create a DatabaseManager instance with temporary database."""
        db_manager = DatabaseManager(str(temp_db_path))
        db_manager.create_tables()
        return db_manager

    def test_database_initialization(self, temp_db_path):
        """Test database initialization."""
        db_manager = DatabaseManager(str(temp_db_path))
        db_manager.create_tables()

        assert db_manager.database_url == f"sqlite:///{temp_db_path}"
        assert db_manager.engine is not None
        assert db_manager.SessionLocal is not None

        # Verify database file was created
        assert temp_db_path.exists()

        # Verify tables were created
        with db_manager.get_session() as session:
            # Try to query each table to verify they exist
            session.query(ProcessedFile).first()
            session.query(FileOperation).first()
            session.query(SystemMetrics).first()

    def test_get_session(self, db_manager):
        """Test getting a database session."""
        with db_manager.get_session() as session:
            assert session is not None
            # Verify it's a proper SQLAlchemy session
            assert hasattr(session, "execute")
            assert hasattr(session, "add")
            assert hasattr(session, "commit")

    def test_record_file_processing_success(self, db_manager):
        """Test successfully recording file processing."""
        file_path = "/test/document.md"
        file_hash = "abc123def456"
        file_size = 1024
        file_type = ".md"

        file_id = db_manager.record_file_processing(
            file_path=file_path,
            file_hash=file_hash,
            file_size=file_size,
            file_type=file_type,
            status=ProcessingStatus.SUCCESS,
            processing_time_ms=1500,
        )

        assert file_id is not None
        assert file_id > 0

    def test_record_file_processing_with_error(self, db_manager):
        """Test recording file processing with error information."""
        file_path = "/test/document.pdf"
        file_hash = "def456ghi789"
        file_size = 2048
        file_type = ".pdf"
        error_message = "Conversion failed"

        file_id = db_manager.record_file_processing(
            file_path=file_path,
            file_hash=file_hash,
            file_size=file_size,
            file_type=file_type,
            status=ProcessingStatus.FAILED,
            error_message=error_message,
            processing_time_ms=5000,
        )

        assert file_id is not None
        assert file_id > 0

    def test_get_file_processing_history_success(self, db_manager):
        """Test successfully retrieving file processing history."""
        file_path = "/test/document.md"

        # First record a file processing
        file_id = db_manager.record_file_processing(
            file_path=file_path,
            file_hash="test_hash_123",
            file_size=1024,
            file_type=".md",
            status=ProcessingStatus.SUCCESS,
        )

        # Retrieve by file path
        retrieved = db_manager.get_file_processing_history(file_path)

        assert retrieved is not None

    def test_get_file_processing_history_not_found(self, db_manager):
        """Test retrieving file processing history when not found."""
        retrieved = db_manager.get_file_processing_history("/nonexistent/file.md")
        assert retrieved is None

    def test_record_file_operation_success(self, db_manager):
        """Test successfully recording a file operation."""
        # First record a file processing
        file_id = db_manager.record_file_processing(
            file_path="/test/document.md",
            file_hash="test_hash",
            file_size=1024,
            file_type=".md",
            status=ProcessingStatus.SUCCESS,
        )

        # Record a file operation
        operation_id = db_manager.record_file_operation(
            file_id=file_id,
            operation_type="convert_markdown_to_pdf",
            status=ProcessingStatus.SUCCESS,
            processing_time_ms=1000,
        )

        assert operation_id is not None
        assert operation_id > 0

    def test_record_metric_success(self, db_manager):
        """Test successfully recording a metric."""
        db_manager.record_metric(
            metric_name="files_processed_total",
            metric_value=42.0,
            tags={"status": "success", "file_type": ".md"},
        )

        # Verify the metric was recorded
        metrics = db_manager.get_metrics("files_processed_total")
        assert len(metrics) > 0

    def test_record_metric_without_tags(self, db_manager):
        """Test recording a metric without tags."""
        db_manager.record_metric(
            metric_name="system_uptime_seconds", metric_value=3600.0
        )

        # Verify the metric was recorded
        metrics = db_manager.get_metrics("system_uptime_seconds")
        assert len(metrics) > 0
