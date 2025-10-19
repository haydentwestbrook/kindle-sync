"""
Unit tests for database models.

Tests the SQLAlchemy models for persistent state management.
"""

from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.models import Base, FileOperation, ProcessedFile, SystemMetrics


class TestDatabaseModels:
    """Test cases for database models."""

    @pytest.fixture
    def engine(self):
        """Create an in-memory SQLite engine for testing."""
        engine = create_engine("sqlite:///:memory:", echo=False)
        Base.metadata.create_all(engine)
        return engine

    @pytest.fixture
    def session(self, engine):
        """Create a database session."""
        Session = sessionmaker(bind=engine)
        session = Session()
        yield session
        session.close()

    def test_processed_file_creation(self, session):
        """Test creating a ProcessedFile record."""
        processed_file = ProcessedFile(
            file_path="/test/path/document.md",
            file_hash="abc123def456",
            file_size=1024,
            file_type=".md",
            status="success",
            processing_time_ms=1500,
        )

        session.add(processed_file)
        session.commit()

        # Verify the record was created
        retrieved = session.query(ProcessedFile).first()
        assert retrieved is not None
        assert retrieved.file_path == "/test/path/document.md"
        assert retrieved.file_hash == "abc123def456"
        assert retrieved.file_size == 1024
        assert retrieved.file_type == ".md"
        assert retrieved.status == "success"
        assert retrieved.processing_time_ms == 1500
        assert retrieved.processed_at is not None
        assert retrieved.error_message is None

    def test_processed_file_with_error(self, session):
        """Test creating a ProcessedFile record with an error."""
        processed_file = ProcessedFile(
            file_path="/test/path/document.pdf",
            file_hash="def456ghi789",
            file_size=2048,
            file_type=".pdf",
            status="failed",
            error_message="Conversion failed",
            processing_time_ms=5000,
        )

        session.add(processed_file)
        session.commit()

        # Verify the record was created
        retrieved = session.query(ProcessedFile).first()
        assert retrieved is not None
        assert retrieved.status == "failed"
        assert retrieved.error_message == "Conversion failed"
        assert retrieved.processing_time_ms == 5000

    def test_file_operation_creation(self, session):
        """Test creating a FileOperation record."""
        # First create a ProcessedFile
        processed_file = ProcessedFile(
            file_path="/test/path/document.md",
            file_hash="abc123def456",
            file_size=1024,
            file_type=".md",
            status="success",
        )
        session.add(processed_file)
        session.commit()

        # Create a FileOperation
        file_operation = FileOperation(
            file_id=processed_file.id,
            operation_type="convert_markdown_to_pdf",
            status="success",
            details="PDF generated successfully",
        )

        session.add(file_operation)
        session.commit()

        # Verify the record was created
        retrieved = session.query(FileOperation).first()
        assert retrieved is not None
        assert retrieved.file_id == processed_file.id
        assert retrieved.operation_type == "convert_markdown_to_pdf"
        assert retrieved.status == "success"
        assert retrieved.details == "PDF generated successfully"
        assert retrieved.timestamp is not None

    def test_file_operation_relationship(self, session):
        """Test the relationship between ProcessedFile and FileOperation."""
        # Create a ProcessedFile
        processed_file = ProcessedFile(
            file_path="/test/path/document.md",
            file_hash="abc123def456",
            file_size=1024,
            file_type=".md",
            status="success",
        )
        session.add(processed_file)
        session.commit()

        # Create multiple FileOperations
        operation1 = FileOperation(
            file_id=processed_file.id,
            operation_type="convert_markdown_to_pdf",
            status="success",
        )
        operation2 = FileOperation(
            file_id=processed_file.id,
            operation_type="send_pdf_to_kindle",
            status="success",
        )

        session.add_all([operation1, operation2])
        session.commit()

        # Test the relationship
        assert len(processed_file.operations) == 2
        assert operation1.file == processed_file
        assert operation2.file == processed_file

    def test_metric_creation(self, session):
        """Test creating a SystemMetrics record."""
        metric = SystemMetrics(
            name="files_processed_total",
            value=42.0,
            labels='{"status": "success", "file_type": ".md"}',
        )

        session.add(metric)
        session.commit()

        # Verify the record was created
        retrieved = session.query(SystemMetrics).first()
        assert retrieved is not None
        assert retrieved.name == "files_processed_total"
        assert retrieved.value == 42.0
        assert retrieved.labels == '{"status": "success", "file_type": ".md"}'
        assert retrieved.timestamp is not None

    def test_metric_without_labels(self, session):
        """Test creating a SystemMetrics record without labels."""
        metric = SystemMetrics(name="system_uptime_seconds", value=3600.0)

        session.add(metric)
        session.commit()

        # Verify the record was created
        retrieved = session.query(SystemMetrics).first()
        assert retrieved is not None
        assert retrieved.name == "system_uptime_seconds"
        assert retrieved.value == 3600.0
        assert retrieved.labels is None

    def test_processed_file_unique_constraint(self, session):
        """Test that file_path is unique."""
        # Create first record
        processed_file1 = ProcessedFile(
            file_path="/test/path/document.md",
            file_hash="abc123def456",
            file_size=1024,
            file_type=".md",
            status="success",
        )
        session.add(processed_file1)
        session.commit()

        # Try to create second record with same file_path
        processed_file2 = ProcessedFile(
            file_path="/test/path/document.md",
            file_hash="def456ghi789",
            file_size=2048,
            file_type=".md",
            status="success",
        )
        session.add(processed_file2)

        # This should raise an integrity error
        with pytest.raises(Exception):  # SQLAlchemy will raise an exception
            session.commit()

    def test_processed_file_required_fields(self, session):
        """Test that required fields are enforced."""
        # Try to create a record without required fields
        processed_file = ProcessedFile()
        session.add(processed_file)

        # This should raise an exception
        with pytest.raises(Exception):  # SQLAlchemy will raise an exception
            session.commit()

    def test_file_operation_foreign_key(self, session):
        """Test that FileOperation requires a valid file_id."""
        # Try to create a FileOperation with non-existent file_id
        file_operation = FileOperation(
            file_id=999,  # Non-existent ID
            operation_type="test_operation",
            status="success",
        )
        session.add(file_operation)

        # This should raise an exception
        with pytest.raises(Exception):  # SQLAlchemy will raise an exception
            session.commit()

    def test_timestamp_auto_generation(self, session):
        """Test that timestamps are automatically generated."""
        before_creation = datetime.utcnow()

        processed_file = ProcessedFile(
            file_path="/test/path/document.md",
            file_hash="abc123def456",
            file_size=1024,
            file_type=".md",
            status="success",
        )
        session.add(processed_file)
        session.commit()

        after_creation = datetime.utcnow()

        # Verify timestamp is within expected range
        assert before_creation <= processed_file.processed_at <= after_creation

    def test_metric_float_values(self, session):
        """Test that SystemMetrics can handle various float values."""
        # Test with integer-like float
        metric1 = SystemMetrics(name="count", value=42.0)

        # Test with decimal float
        metric2 = SystemMetrics(name="rate", value=0.95)

        # Test with large float
        metric3 = SystemMetrics(name="size", value=1234567.89)

        session.add_all([metric1, metric2, metric3])
        session.commit()

        # Verify all were stored correctly
        metrics = session.query(SystemMetrics).all()
        assert len(metrics) == 3

        values = [m.value for m in metrics]
        assert 42.0 in values
        assert 0.95 in values
        assert 1234567.89 in values
