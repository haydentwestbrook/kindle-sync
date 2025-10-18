"""
Unit tests for AsyncSyncProcessor.

Tests the asynchronous file processing functionality.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path
import tempfile
import os

from src.core.async_processor import AsyncSyncProcessor, ProcessingResult
from src.config import Config
from src.database.manager import DatabaseManager
from src.core.exceptions import FileProcessingError, EmailServiceError, ErrorSeverity


class TestAsyncSyncProcessor:
    """Test cases for AsyncSyncProcessor."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration."""
        config = Mock(spec=Config)
        config.get.side_effect = lambda key, default=None: {
            "advanced.max_file_size_mb": 50,
            "patterns.allowed_extensions": [".md", ".pdf", ".txt"],
            "patterns.allowed_mime_types": ["text/markdown", "application/pdf", "text/plain"],
            "advanced.retry_attempts": 3
        }.get(key, default)
        return config

    @pytest.fixture
    def mock_db_manager(self):
        """Create a mock database manager."""
        db_manager = Mock(spec=DatabaseManager)
        db_manager.get_processed_file_by_hash.return_value = None
        db_manager.add_processed_file.return_value = Mock(id=1)
        db_manager.add_file_operation.return_value = Mock(id=1)
        return db_manager

    @pytest.fixture
    def processor(self, mock_config, mock_db_manager):
        """Create an AsyncSyncProcessor instance."""
        with patch('src.core.async_processor.KindleSync'), \
             patch('src.core.async_processor.MarkdownToPDFConverter'), \
             patch('src.core.async_processor.PDFToMarkdownConverter'), \
             patch('src.core.async_processor.FileValidator'), \
             patch('src.core.async_processor.ErrorHandler'):
            return AsyncSyncProcessor(mock_config, mock_db_manager, max_workers=2)

    @pytest.mark.asyncio
    async def test_process_file_async_success(self, processor, mock_db_manager):
        """Test successful async file processing."""
        with tempfile.NamedTemporaryFile(suffix='.md', delete=False) as temp_file:
            temp_file.write(b"# Test Document\n\nThis is a test.")
            temp_file.flush()
            temp_path = Path(temp_file.name)

        try:
            # Mock the file validation and processing
            processor.file_validator.calculate_checksum.return_value = "test_hash"
            processor.file_validator.validate_file.return_value = Mock(
                valid=True,
                checksum="test_hash"
            )
            processor.markdown_to_pdf.convert_markdown_to_pdf.return_value = temp_path.with_suffix('.pdf')
            processor._send_pdf_to_kindle_async = AsyncMock(return_value=True)

            result = await processor.process_file_async(temp_path)

            assert result.success is True
            assert result.file_path == temp_path
            assert result.file_hash == "test_hash"
            assert result.processing_time_ms is not None
            assert result.processing_time_ms > 0

            # Verify database operations
            mock_db_manager.add_processed_file.assert_called_once()
            assert mock_db_manager.add_processed_file.call_args[1]['status'] == 'success'

        finally:
            os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_process_file_async_validation_failure(self, processor, mock_db_manager):
        """Test async file processing with validation failure."""
        with tempfile.NamedTemporaryFile(suffix='.md', delete=False) as temp_file:
            temp_file.write(b"# Test Document\n\nThis is a test.")
            temp_file.flush()
            temp_path = Path(temp_file.name)

        try:
            # Mock validation failure
            processor.file_validator.calculate_checksum.return_value = "test_hash"
            processor.file_validator.validate_file.return_value = Mock(
                valid=False,
                error="File too large"
            )

            result = await processor.process_file_async(temp_path)

            assert result.success is False
            assert result.file_path == temp_path
            assert "File validation failed" in result.error
            assert result.file_hash == "test_hash"

            # Verify database operations
            mock_db_manager.add_processed_file.assert_called_once()
            assert mock_db_manager.add_processed_file.call_args[1]['status'] == 'failed'

        finally:
            os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_process_file_async_already_processed(self, processor, mock_db_manager):
        """Test async file processing when file is already processed."""
        with tempfile.NamedTemporaryFile(suffix='.md', delete=False) as temp_file:
            temp_file.write(b"# Test Document\n\nThis is a test.")
            temp_file.flush()
            temp_path = Path(temp_file.name)

        try:
            # Mock that file is already processed
            processor.file_validator.calculate_checksum.return_value = "test_hash"
            mock_db_manager.get_processed_file_by_hash.return_value = Mock(id=1, status="success")

            result = await processor.process_file_async(temp_path)

            assert result.success is True
            assert result.file_path == temp_path
            assert result.error == "File already processed"

            # Verify no new database record was added
            mock_db_manager.add_processed_file.assert_not_called()

        finally:
            os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_process_file_async_conversion_failure(self, processor, mock_db_manager):
        """Test async file processing with conversion failure."""
        with tempfile.NamedTemporaryFile(suffix='.md', delete=False) as temp_file:
            temp_file.write(b"# Test Document\n\nThis is a test.")
            temp_file.flush()
            temp_path = Path(temp_file.name)

        try:
            # Mock validation success but conversion failure
            processor.file_validator.calculate_checksum.return_value = "test_hash"
            processor.file_validator.validate_file.return_value = Mock(
                valid=True,
                checksum="test_hash"
            )
            processor.markdown_to_pdf.convert_markdown_to_pdf.return_value = None

            result = await processor.process_file_async(temp_path)

            assert result.success is False
            assert result.file_path == temp_path
            assert "Markdown to PDF conversion failed" in result.error

            # Verify database operations
            mock_db_manager.add_processed_file.assert_called_once()
            assert mock_db_manager.add_processed_file.call_args[1]['status'] == 'failed'

        finally:
            os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_process_file_async_retry_logic(self, processor, mock_db_manager):
        """Test async file processing with retry logic."""
        with tempfile.NamedTemporaryFile(suffix='.md', delete=False) as temp_file:
            temp_file.write(b"# Test Document\n\nThis is a test.")
            temp_file.flush()
            temp_path = Path(temp_file.name)

        try:
            # Mock validation success but email sending failure
            processor.file_validator.calculate_checksum.return_value = "test_hash"
            processor.file_validator.validate_file.return_value = Mock(
                valid=True,
                checksum="test_hash"
            )
            processor.markdown_to_pdf.convert_markdown_to_pdf.return_value = temp_path.with_suffix('.pdf')
            
            # Mock email sending to fail twice, then succeed
            processor._send_pdf_to_kindle_async = AsyncMock(side_effect=[
                EmailServiceError("SMTP error", severity=ErrorSeverity.MEDIUM),
                EmailServiceError("SMTP error", severity=ErrorSeverity.MEDIUM),
                True
            ])

            result = await processor.process_file_async(temp_path)

            assert result.success is True
            assert result.file_path == temp_path

            # Verify retry attempts
            assert processor._send_pdf_to_kindle_async.call_count == 3

        finally:
            os.unlink(temp_path)

    def test_shutdown(self, processor):
        """Test processor shutdown."""
        # Mock the executor
        processor.executor = Mock()
        
        processor.shutdown()
        
        processor.executor.shutdown.assert_called_once_with(wait=True)

    @pytest.mark.asyncio
    async def test_send_pdf_to_kindle_async(self, processor):
        """Test async PDF sending to Kindle."""
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
            temp_file.write(b"%PDF-1.4\nTest PDF content")
            temp_file.flush()
            temp_path = Path(temp_file.name)

        try:
            # Mock the synchronous send_pdf_to_kindle method
            processor.kindle_sync.send_pdf_to_kindle.return_value = True

            result = await processor._send_pdf_to_kindle_async(temp_path)

            assert result is True
            processor.kindle_sync.send_pdf_to_kindle.assert_called_once_with(temp_path)

        finally:
            os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_process_single_file_markdown(self, processor):
        """Test processing a single markdown file."""
        with tempfile.NamedTemporaryFile(suffix='.md', delete=False) as temp_file:
            temp_file.write(b"# Test Document\n\nThis is a test.")
            temp_file.flush()
            temp_path = Path(temp_file.name)

        try:
            # Mock validation
            processor.file_validator.validate_file.return_value = Mock(
                valid=True,
                checksum="test_hash"
            )
            
            # Mock conversion
            processor.markdown_to_pdf.convert_markdown_to_pdf.return_value = temp_path.with_suffix('.pdf')
            
            # Mock email sending
            processor._send_pdf_to_kindle_async = AsyncMock(return_value=True)

            result = await processor._process_single_file(temp_path)

            assert result.success is True
            assert result.file_path == temp_path
            assert result.output_path == temp_path.with_suffix('.pdf')

        finally:
            os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_process_single_file_pdf(self, processor):
        """Test processing a single PDF file."""
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
            temp_file.write(b"%PDF-1.4\nTest PDF content")
            temp_file.flush()
            temp_path = Path(temp_file.name)

        try:
            # Mock validation
            processor.file_validator.validate_file.return_value = Mock(
                valid=True,
                checksum="test_hash"
            )
            
            # Mock conversion
            processor.pdf_to_markdown.convert_pdf_to_markdown.return_value = temp_path.with_suffix('.md')

            result = await processor._process_single_file(temp_path)

            assert result.success is True
            assert result.file_path == temp_path
            assert result.output_path == temp_path.with_suffix('.md')

        finally:
            os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_process_single_file_unsupported_type(self, processor):
        """Test processing an unsupported file type."""
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as temp_file:
            temp_file.write(b"Plain text content")
            temp_file.flush()
            temp_path = Path(temp_file.name)

        try:
            # Mock validation
            processor.file_validator.validate_file.return_value = Mock(
                valid=True,
                checksum="test_hash"
            )

            result = await processor._process_single_file(temp_path)

            assert result.success is False
            assert result.file_path == temp_path
            assert "Unsupported file type" in result.error

        finally:
            os.unlink(temp_path)
