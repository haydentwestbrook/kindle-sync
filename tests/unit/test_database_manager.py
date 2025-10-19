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
from src.database.models import FileOperation, ProcessedFile, SystemMetrics


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
        return DatabaseManager(temp_db_path)

    def test_database_initialization(self, temp_db_path):
        """Test database initialization."""
        db_manager = DatabaseManager(temp_db_path)

        assert db_manager.db_path == temp_db_path
        assert db_manager.engine is not None
        assert db_manager.Session is not None

        # Verify database file was created
        assert temp_db_path.exists()

        # Verify tables were created
        with db_manager.get_session() as session:
            # Try to query each table to verify they exist
            session.query(ProcessedFile).first()
            session.query(FileOperation).first()
            session.query(SystemMetrics).first()

    def test_database_initialization_with_nonexistent_directory(self):
        """Test database initialization with non-existent directory."""
        temp_path = Path("/tmp/nonexistent/dir/test.db")

        db_manager = DatabaseManager(temp_path)

        # Verify parent directory was created
        assert temp_path.parent.exists()
        assert temp_path.exists()

    def test_database_initialization_failure(self):
        """Test database initialization failure."""
        # Mock SQLAlchemyError to simulate initialization failure
        with patch("src.database.manager.create_engine") as mock_engine:
            mock_engine.side_effect = SQLAlchemyError("Connection failed")

            with pytest.raises(KindleSyncError) as exc_info:
                DatabaseManager(Path("/tmp/test.db"))

            assert exc_info.value.severity == ErrorSeverity.CRITICAL
            assert "Failed to initialize database" in str(exc_info.value)

    def test_get_session(self, db_manager):
        """Test getting a database session."""
        session = db_manager.get_session()

        assert session is not None
        # Verify it's a proper SQLAlchemy session
        assert hasattr(session, "query")
        assert hasattr(session, "add")
        assert hasattr(session, "commit")

    def test_get_session_failure(self):
        """Test getting a session when database is not initialized."""
        db_manager = DatabaseManager(Path("/tmp/test.db"))
        db_manager.Session = None  # Simulate uninitialized state

        with pytest.raises(KindleSyncError) as exc_info:
            db_manager.get_session()

        assert exc_info.value.severity == ErrorSeverity.CRITICAL
        assert "Database not initialized" in str(exc_info.value)

    def test_add_processed_file_success(self, db_manager):
        """Test successfully adding a processed file."""
        file_path = Path("/test/document.md")
        file_hash = "abc123def456"
        file_size = 1024
        file_type = ".md"

        processed_file = db_manager.add_processed_file(
            file_path=file_path,
            file_hash=file_hash,
            file_size=file_size,
            file_type=file_type,
            status="success",
            processing_time_ms=1500,
        )

        assert processed_file is not None
        assert processed_file.file_path == str(file_path)
        assert processed_file.file_hash == file_hash
        assert processed_file.file_size == file_size
        assert processed_file.file_type == file_type
        assert processed_file.status == "success"
        assert processed_file.processing_time_ms == 1500
        assert processed_file.id is not None

    def test_add_processed_file_with_error(self, db_manager):
        """Test adding a processed file with error information."""
        file_path = Path("/test/document.pdf")
        file_hash = "def456ghi789"
        file_size = 2048
        file_type = ".pdf"
        error_message = "Conversion failed"

        processed_file = db_manager.add_processed_file(
            file_path=file_path,
            file_hash=file_hash,
            file_size=file_size,
            file_type=file_type,
            status="failed",
            error_message=error_message,
            processing_time_ms=5000,
        )

        assert processed_file.status == "failed"
        assert processed_file.error_message == error_message
        assert processed_file.processing_time_ms == 5000

    def test_add_processed_file_database_error(self, db_manager):
        """Test adding a processed file with database error."""
        # Mock SQLAlchemyError
        with patch.object(db_manager, "get_session") as mock_get_session:
            mock_session = Mock()
            mock_session.add.side_effect = SQLAlchemyError("Database error")
            mock_get_session.return_value.__enter__.return_value = mock_session

            with pytest.raises(KindleSyncError) as exc_info:
                db_manager.add_processed_file(
                    file_path=Path("/test/document.md"),
                    file_hash="test_hash",
                    file_size=1024,
                    file_type=".md",
                )

            assert "Failed to add processed file" in str(exc_info.value)
            mock_session.rollback.assert_called_once()

    def test_update_processed_file_status_success(self, db_manager):
        """Test successfully updating processed file status."""
        # First add a processed file
        processed_file = db_manager.add_processed_file(
            file_path=Path("/test/document.md"),
            file_hash="test_hash",
            file_size=1024,
            file_type=".md",
            status="processing",
        )

        # Update the status
        db_manager.update_processed_file_status(
            file_id=processed_file.id, status="success", processing_time_ms=2000
        )

        # Verify the update
        with db_manager.get_session() as session:
            updated_file = (
                session.query(ProcessedFile).filter_by(id=processed_file.id).first()
            )
            assert updated_file.status == "success"
            assert updated_file.processing_time_ms == 2000

    def test_update_processed_file_status_not_found(self, db_manager):
        """Test updating status for non-existent file."""
        # This should not raise an exception, just log a warning
        db_manager.update_processed_file_status(
            file_id=999, status="success"  # Non-existent ID
        )

        # No exception should be raised

    def test_get_processed_file_by_hash_success(self, db_manager):
        """Test successfully retrieving a processed file by hash."""
        file_hash = "test_hash_123"

        # Add a processed file
        processed_file = db_manager.add_processed_file(
            file_path=Path("/test/document.md"),
            file_hash=file_hash,
            file_size=1024,
            file_type=".md",
        )

        # Retrieve by hash
        retrieved = db_manager.get_processed_file_by_hash(file_hash)

        assert retrieved is not None
        assert retrieved.id == processed_file.id
        assert retrieved.file_hash == file_hash

    def test_get_processed_file_by_hash_not_found(self, db_manager):
        """Test retrieving a processed file by hash when not found."""
        retrieved = db_manager.get_processed_file_by_hash("nonexistent_hash")
        assert retrieved is None

    def test_add_file_operation_success(self, db_manager):
        """Test successfully adding a file operation."""
        # First add a processed file
        processed_file = db_manager.add_processed_file(
            file_path=Path("/test/document.md"),
            file_hash="test_hash",
            file_size=1024,
            file_type=".md",
        )

        # Add a file operation
        file_operation = db_manager.add_file_operation(
            file_id=processed_file.id,
            operation_type="convert_markdown_to_pdf",
            status="success",
            details="PDF generated successfully",
        )

        assert file_operation is not None
        assert file_operation.file_id == processed_file.id
        assert file_operation.operation_type == "convert_markdown_to_pdf"
        assert file_operation.status == "success"
        assert file_operation.details == "PDF generated successfully"
        assert file_operation.id is not None

    def test_add_file_operation_database_error(self, db_manager):
        """Test adding a file operation with database error."""
        # Mock SQLAlchemyError
        with patch.object(db_manager, "get_session") as mock_get_session:
            mock_session = Mock()
            mock_session.add.side_effect = SQLAlchemyError("Database error")
            mock_get_session.return_value.__enter__.return_value = mock_session

            with pytest.raises(KindleSyncError) as exc_info:
                db_manager.add_file_operation(
                    file_id=1, operation_type="test_operation", status="success"
                )

            assert "Failed to add file operation" in str(exc_info.value)
            mock_session.rollback.assert_called_once()

    def test_add_metric_success(self, db_manager):
        """Test successfully adding a metric."""
        db_manager.add_metric(
            name="files_processed_total",
            value=42.0,
            labels={"status": "success", "file_type": ".md"},
        )

        # Verify the metric was added
        with db_manager.get_session() as session:
            metric = session.query(SystemMetrics).first()
            assert metric is not None
            assert metric.name == "files_processed_total"
            assert metric.value == 42.0
            assert metric.labels == str({"status": "success", "file_type": ".md"})

    def test_add_metric_without_labels(self, db_manager):
        """Test adding a metric without labels."""
        db_manager.add_metric(name="system_uptime_seconds", value=3600.0)

        # Verify the metric was added
        with db_manager.get_session() as session:
            metric = session.query(SystemMetrics).first()
            assert metric is not None
            assert metric.name == "system_uptime_seconds"
            assert metric.value == 3600.0
            assert metric.labels is None

    def test_add_metric_database_error(self, db_manager):
        """Test adding a metric with database error."""
        # Mock SQLAlchemyError
        with patch.object(db_manager, "get_session") as mock_get_session:
            mock_session = Mock()
            mock_session.add.side_effect = SQLAlchemyError("Database error")
            mock_get_session.return_value.__enter__.return_value = mock_session

            with pytest.raises(KindleSyncError) as exc_info:
                db_manager.add_metric(name="test_metric", value=1.0)

            assert "Failed to add metric" in str(exc_info.value)
            mock_session.rollback.assert_called_once()

    def test_get_all_processed_files(self, db_manager):
        """Test retrieving all processed files."""
        # Add multiple processed files
        file1 = db_manager.add_processed_file(
            file_path=Path("/test/document1.md"),
            file_hash="hash1",
            file_size=1024,
            file_type=".md",
        )
        file2 = db_manager.add_processed_file(
            file_path=Path("/test/document2.pdf"),
            file_hash="hash2",
            file_size=2048,
            file_type=".pdf",
        )

        # Retrieve all files
        all_files = db_manager.get_all_processed_files()

        assert len(all_files) == 2
        file_ids = [f.id for f in all_files]
        assert file1.id in file_ids
        assert file2.id in file_ids

    def test_close(self, db_manager):
        """Test closing the database connection."""
        # Mock the engine
        mock_engine = Mock()
        db_manager.engine = mock_engine

        db_manager.close()

        mock_engine.dispose.assert_called_once()

    def test_close_without_engine(self, db_manager):
        """Test closing when engine is None."""
        db_manager.engine = None

        # Should not raise an exception
        db_manager.close()
