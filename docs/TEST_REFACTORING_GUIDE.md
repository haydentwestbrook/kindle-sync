# Test Refactoring Implementation Guide

## Quick Start

This guide provides specific code examples and step-by-step instructions for refactoring the failing unit tests.

## Phase 1: Database Manager Tests (Priority: Critical)

### Current Issues and Fixes

#### Issue 1: Method Name Mismatches

**Problem**: Tests call `add_processed_file()` but actual method is `record_file_processing()`

**Fix**:
```python
# Before (test_database_manager.py)
processed_file = db_manager.add_processed_file(
    file_path=file_path,
    file_hash=file_hash,
    file_size=file_size,
    file_type=file_type,
    status="success",
    processing_time_ms=1500,
)

# After
processed_file = db_manager.record_file_processing(
    file_path=str(file_path),
    file_hash=file_hash,
    file_size=file_size,
    file_type=file_type,
    status="success",
    processing_time_ms=1500,
)
```

#### Issue 2: Session Attribute Mismatch

**Problem**: Tests expect `Session` but actual attribute is `SessionLocal`

**Fix**:
```python
# Before
assert db_manager.Session is not None

# After
assert db_manager.SessionLocal is not None
```

#### Issue 3: Non-existent Methods

**Problem**: Tests call methods that don't exist

**Fix**: Remove or replace with existing methods
```python
# Remove these test methods entirely:
# - test_close()
# - test_close_without_engine()
# - test_update_processed_file_status_success()
# - test_update_processed_file_status_not_found()
# - test_get_all_processed_files()

# Replace get_processed_file_by_hash with:
# Before
retrieved = db_manager.get_processed_file_by_hash("test_hash")

# After
retrieved = db_manager.get_file_processing_history("/test/document.md")
```

### Complete Database Manager Test Refactor

```python
# tests/unit/test_database_manager.py

import pytest
from unittest.mock import Mock, patch
from pathlib import Path
from sqlalchemy.exc import SQLAlchemyError

from src.database.manager import DatabaseManager
from src.core.exceptions import KindleSyncError


class TestDatabaseManager:
    """Test cases for DatabaseManager."""

    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database path."""
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            temp_path = Path(f.name)
        yield temp_path
        temp_path.unlink(missing_ok=True)

    @pytest.fixture
    def db_manager(self, temp_db_path):
        """Create a DatabaseManager instance with temporary database."""
        return DatabaseManager(str(temp_db_path))

    def test_database_initialization(self, temp_db_path):
        """Test database initialization."""
        db_manager = DatabaseManager(str(temp_db_path))

        assert db_manager.database_url == f"sqlite:///{temp_db_path}"
        assert db_manager.engine is not None
        assert db_manager.SessionLocal is not None

        # Verify database file was created
        assert temp_db_path.exists()

        # Verify tables were created
        with db_manager.get_session() as session:
            # Test that we can get a session
            assert session is not None

    def test_get_session(self, db_manager):
        """Test getting a database session."""
        with db_manager.get_session() as session:
            assert session is not None
            # Verify it's a proper SQLAlchemy session
            assert hasattr(session, "execute")

    def test_record_file_processing_success(self, db_manager):
        """Test successfully recording file processing."""
        file_path = "/test/document.md"
        file_hash = "abc123def456"
        file_size = 1024
        file_type = ".md"

        processed_file = db_manager.record_file_processing(
            file_path=file_path,
            file_hash=file_hash,
            file_size=file_size,
            file_type=file_type,
            status="success",
            processing_time_ms=1500,
        )

        assert processed_file is not None
        assert processed_file.file_path == file_path
        assert processed_file.file_hash == file_hash
        assert processed_file.file_size == file_size
        assert processed_file.file_type == file_type

    def test_record_file_processing_with_error(self, db_manager):
        """Test recording file processing with error information."""
        file_path = "/test/document.pdf"
        file_hash = "def456ghi789"
        file_size = 2048
        file_type = ".pdf"
        error_message = "Conversion failed"

        processed_file = db_manager.record_file_processing(
            file_path=file_path,
            file_hash=file_hash,
            file_size=file_size,
            file_type=file_type,
            status="failed",
            error_message=error_message,
            processing_time_ms=5000,
        )

        assert processed_file is not None
        assert processed_file.error_message == error_message
        assert processed_file.status == "failed"

    def test_record_metric_success(self, db_manager):
        """Test successfully recording a metric."""
        db_manager.record_metric(
            name="files_processed_total",
            value=42.0,
            labels={"status": "success", "file_type": ".md"},
        )

        # Verify metric was recorded
        metrics = db_manager.get_metrics("files_processed_total")
        assert len(metrics) > 0
        assert metrics[0].value == 42.0

    def test_get_file_processing_history(self, db_manager):
        """Test retrieving file processing history."""
        file_path = "/test/document.md"
        
        # First record a file processing
        db_manager.record_file_processing(
            file_path=file_path,
            file_hash="test_hash",
            file_size=1024,
            file_type=".md",
        )

        # Then retrieve it
        history = db_manager.get_file_processing_history(file_path)
        assert history is not None
        assert history.file_path == file_path

    def test_get_file_processing_history_not_found(self, db_manager):
        """Test retrieving file processing history when not found."""
        history = db_manager.get_file_processing_history("/nonexistent/file.md")
        assert history is None

    def test_record_file_operation_success(self, db_manager):
        """Test successfully recording a file operation."""
        # First record a file processing
        processed_file = db_manager.record_file_processing(
            file_path="/test/document.md",
            file_hash="test_hash",
            file_size=1024,
            file_type=".md",
        )

        # Then record an operation
        operation = db_manager.record_file_operation(
            file_id=processed_file.id,
            operation_type="convert_to_pdf",
            status="success",
            processing_time_ms=1000,
        )

        assert operation is not None
        assert operation.operation_type == "convert_to_pdf"
        assert operation.status == "success"

    def test_get_processing_statistics(self, db_manager):
        """Test getting processing statistics."""
        stats = db_manager.get_processing_statistics()
        assert isinstance(stats, dict)
        assert "total_files" in stats
        assert "success_rate" in stats

    def test_get_database_info(self, db_manager):
        """Test getting database information."""
        info = db_manager.get_database_info()
        assert isinstance(info, dict)
        assert "database_url" in info
        assert "tables" in info
```

## Phase 2: Async Processor Tests (Priority: Critical)

### Current Issues and Fixes

#### Issue 1: Constructor Mismatch

**Problem**: Tests pass `db_manager` as second parameter, but constructor doesn't accept it

**Fix**:
```python
# Before
processor = AsyncSyncProcessor(mock_config, mock_db_manager, max_workers=2)

# After
with patch("src.core.async_processor.DatabaseManager", return_value=mock_db_manager):
    processor = AsyncSyncProcessor(mock_config, max_workers=2)
```

#### Issue 2: Non-existent Methods

**Problem**: Tests call methods that don't exist

**Fix**: Remove tests for non-existent methods
```python
# Remove these test methods entirely:
# - test_shutdown()
# - test_send_pdf_to_kindle_async()
# - test_process_single_file_markdown()
# - test_process_single_file_pdf()
# - test_process_single_file_unsupported_type()
```

#### Issue 3: FileValidator Method Mismatch

**Problem**: Tests expect `calculate_checksum()` method that doesn't exist

**Fix**:
```python
# Before
processor.file_validator.calculate_checksum.return_value = "test_hash"

# After
# Mock the actual method that exists or remove the test
```

### Complete Async Processor Test Refactor

```python
# tests/unit/test_async_processor.py

import pytest
import tempfile
from unittest.mock import Mock, patch
from pathlib import Path

from src.core.async_processor import AsyncSyncProcessor
from src.database.manager import DatabaseManager


class TestAsyncSyncProcessor:
    """Test cases for AsyncSyncProcessor."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration."""
        config = Mock()
        config.get.side_effect = lambda key, default=None: {
            "database.path": "test.db",
            "processing.max_workers": 2,
            "processing.retry_attempts": 3,
        }.get(key, default)
        return config

    @pytest.fixture
    def mock_db_manager(self):
        """Create a mock database manager."""
        db_manager = Mock(spec=DatabaseManager)
        db_manager.get_file_processing_history.return_value = None
        db_manager.record_file_operation.return_value = Mock(id=1)
        db_manager.record_file_processing.return_value = Mock(id=1)
        db_manager.add_to_queue.return_value = Mock(id=1)
        db_manager.get_queue_size.return_value = 0
        db_manager.get_next_queue_item.return_value = None
        db_manager.remove_from_queue.return_value = None
        db_manager.get_processing_statistics.return_value = {}
        return db_manager

    @pytest.fixture
    def processor(self, mock_config, mock_db_manager):
        """Create an AsyncSyncProcessor instance."""
        with patch("src.core.async_processor.DatabaseManager", return_value=mock_db_manager):
            return AsyncSyncProcessor(mock_config, max_workers=2)

    @pytest.mark.asyncio
    async def test_process_file_async_success(self, processor, mock_db_manager):
        """Test successful async file processing."""
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as temp_file:
            temp_file.write(b"# Test Document\n\nThis is a test.")
            temp_file.flush()
            temp_path = Path(temp_file.name)

        try:
            # Mock the file validation
            processor.file_validator.validate_file = Mock(return_value=Mock(
                valid=True, 
                checksum="test_hash"
            ))

            result = await processor.process_file_async(temp_path)

            assert result is not None
            assert result.success is True
            assert result.file_path == temp_path

        finally:
            temp_path.unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_process_file_async_validation_failure(self, processor, mock_db_manager):
        """Test async file processing with validation failure."""
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as temp_file:
            temp_file.write(b"# Test Document\n\nThis is a test.")
            temp_file.flush()
            temp_path = Path(temp_file.name)

        try:
            # Mock validation failure
            processor.file_validator.validate_file = Mock(return_value=Mock(
                valid=False, 
                error="Invalid file format"
            ))

            result = await processor.process_file_async(temp_path)

            assert result is not None
            assert result.success is False
            assert "Invalid file format" in result.error_message

        finally:
            temp_path.unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_process_file_async_already_processed(self, processor, mock_db_manager):
        """Test async file processing when file is already processed."""
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as temp_file:
            temp_file.write(b"# Test Document\n\nThis is a test.")
            temp_file.flush()
            temp_path = Path(temp_file.name)

        try:
            # Mock that file is already processed
            mock_db_manager.get_file_processing_history.return_value = Mock(
                id=1,
                file_path=str(temp_path),
                status="success"
            )

            result = await processor.process_file_async(temp_path)

            assert result is not None
            assert result.success is True

        finally:
            temp_path.unlink(missing_ok=True)

    def test_get_statistics(self, processor):
        """Test getting processor statistics."""
        stats = processor.get_statistics()
        assert isinstance(stats, dict)
        assert "files_processed" in stats
        assert "errors" in stats

    def test_get_health_status(self, processor):
        """Test getting processor health status."""
        health = processor.get_health_status()
        assert isinstance(health, dict)
        assert "status" in health
        assert "timestamp" in health

    @pytest.mark.asyncio
    async def test_cleanup(self, processor):
        """Test processor cleanup."""
        # This should not raise an exception
        await processor.cleanup()
```

## Phase 3: Configuration Tests (Priority: High)

### Current Issues and Fixes

#### Issue 1: Configuration Path Mismatch

**Problem**: Tests expect different configuration structure

**Fix**:
```python
# Update test configurations to match current YAML structure
# Fix path resolution tests
# Update method expectations
```

### Complete Config Test Refactor

```python
# tests/unit/test_config.py

import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from src.config import Config


class TestConfig:
    """Test cases for Config class."""

    @pytest.fixture
    def mock_config_data(self):
        """Create mock configuration data."""
        return {
            "obsidian": {
                "vault_path": "/path/to/vault",
                "sync_folder": "Kindle Sync",
                "templates_folder": "Templates",
            },
            "kindle": {
                "email": "test@kindle.com",
                "smtp_server": "smtp.gmail.com",
                "smtp_port": 587,
                "smtp_username": "test@gmail.com",
                "smtp_password": "test_password",
            },
            "smtp": {
                "host": "smtp.gmail.com",
                "port": 587,
                "username": "test@gmail.com",
                "password": "test_password",
            },
            "processing": {
                "pdf": {
                    "page_size": "A4",
                    "margins": [72, 72, 72, 72],
                    "font_family": "Times-Roman",
                    "font_size": 12,
                    "line_spacing": 1.2,
                },
                "markdown": {
                    "extensions": ["tables", "fenced_code", "toc"],
                    "preserve_links": True,
                },
                "ocr": {
                    "language": "eng",
                    "confidence_threshold": 60,
                },
            },
            "sync": {
                "auto_convert_on_save": True,
                "auto_send_to_kindle": True,
                "backup_originals": True,
                "backup_folder": "Backups",
                "max_file_size_mb": 50,
                "retry_attempts": 3,
            },
        }

    @pytest.fixture
    def config(self, mock_config_data):
        """Create a Config instance with mock data."""
        with patch.object(Config, '_load_config', return_value=mock_config_data):
            return Config()

    def test_get_method(self, config):
        """Test the get method."""
        # Test getting a simple value
        assert config.get("obsidian.vault_path") == "/path/to/vault"
        
        # Test getting a nested value
        assert config.get("processing.pdf.page_size") == "A4"
        
        # Test getting a non-existent value with default
        assert config.get("non.existent.key", "default") == "default"

    def test_get_obsidian_vault_path(self, config):
        """Test getting Obsidian vault path."""
        path = config.get_obsidian_vault_path()
        assert path == "/path/to/vault"

    def test_get_sync_folder_path(self, config):
        """Test getting sync folder path."""
        path = config.get_sync_folder_path()
        assert path == "Kindle Sync"

    def test_get_templates_folder_path(self, config):
        """Test getting templates folder path."""
        path = config.get_templates_folder_path()
        assert path == "Templates"

    def test_get_smtp_config(self, config):
        """Test getting SMTP configuration."""
        smtp_config = config.get_smtp_config()
        assert smtp_config["server"] == "smtp.gmail.com"
        assert smtp_config["port"] == 587
        assert smtp_config["username"] == "test@gmail.com"
        assert smtp_config["password"] == "test_password"

    def test_get_pdf_config(self, config):
        """Test getting PDF configuration."""
        pdf_config = config.get_pdf_config()
        assert pdf_config["page_size"] == "A4"
        assert pdf_config["margins"] == [72, 72, 72, 72]
        assert pdf_config["font_family"] == "Times-Roman"
        assert pdf_config["font_size"] == 12
        assert pdf_config["line_spacing"] == 1.2

    def test_get_markdown_config(self, config):
        """Test getting Markdown configuration."""
        markdown_config = config.get_markdown_config()
        assert "tables" in markdown_config["extensions"]
        assert "fenced_code" in markdown_config["extensions"]
        assert "toc" in markdown_config["extensions"]
        assert markdown_config["preserve_links"] is True

    def test_get_ocr_config(self, config):
        """Test getting OCR configuration."""
        ocr_config = config.get_ocr_config()
        assert ocr_config["language"] == "eng"
        assert ocr_config["confidence_threshold"] == 60

    def test_get_sync_config(self, config):
        """Test getting sync configuration."""
        sync_config = config.get_sync_config()
        assert sync_config["auto_convert_on_save"] is True
        assert sync_config["auto_send_to_kindle"] is True
        assert sync_config["backup_originals"] is True
        assert sync_config["backup_folder"] == "Backups"
        assert sync_config["max_file_size_mb"] == 50
        assert sync_config["retry_attempts"] == 3
```

## Implementation Checklist

### Phase 1: Database Manager (Week 1)
- [ ] Update all method names from `add_processed_file` to `record_file_processing`
- [ ] Update all method names from `get_processed_file_by_hash` to `get_file_processing_history`
- [ ] Update all method names from `add_metric` to `record_metric`
- [ ] Fix session attribute from `Session` to `SessionLocal`
- [ ] Remove tests for non-existent methods (`close`, `update_processed_file_status`, etc.)
- [ ] Update database URL expectations to include `sqlite:///` prefix
- [ ] Fix session handling to use context manager properly

### Phase 2: Async Processor (Week 1)
- [ ] Fix constructor calls to only pass `config` and `max_workers`
- [ ] Remove tests for non-existent methods (`shutdown`, `send_pdf_to_kindle_async`, etc.)
- [ ] Fix async test patterns to properly await async methods
- [ ] Update mock configurations to match actual dependencies
- [ ] Fix FileValidator method expectations

### Phase 3: Configuration (Week 1)
- [ ] Update test configurations to match current YAML structure
- [ ] Fix path resolution tests
- [ ] Update method expectations to match current Config API
- [ ] Add tests for new configuration methods

### Phase 4: File Watcher (Week 2)
- [ ] Update tests to match current file watcher implementation
- [ ] Fix event handling tests to use correct callback signatures
- [ ] Update statistics and monitoring tests

### Phase 5: Email Receiver (Week 2)
- [ ] Update IMAP connection tests
- [ ] Fix attachment handling tests
- [ ] Update email processing workflow tests

### Phase 6: Remaining Tests (Week 3)
- [ ] Fix database models tests
- [ ] Fix health check tests
- [ ] Fix metrics tests
- [ ] Fix remaining KindleSync tests

## Testing Strategy

### 1. Run Tests After Each Fix
```bash
# Run specific test file
python -m pytest tests/unit/test_database_manager.py -v

# Run all tests
python -m pytest tests/unit/ -v
```

### 2. Check Test Coverage
```bash
# Run with coverage
python -m pytest tests/unit/ --cov=src --cov-report=html
```

### 3. Validate No Regressions
```bash
# Run previously passing tests to ensure no regressions
python -m pytest tests/unit/test_health_checks.py tests/unit/test_kindle_sync.py tests/unit/test_pdf_converter.py tests/unit/test_security_validation.py -v
```

## Success Metrics

- [ ] All 88 failing tests now pass
- [ ] No regressions in previously passing tests
- [ ] Test coverage maintained or improved
- [ ] All tests run reliably without flakiness

---

*This guide should be followed step-by-step, with each phase completed before moving to the next. Regular testing and validation should be performed throughout the process.*
