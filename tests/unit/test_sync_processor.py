"""Unit tests for sync processor functionality."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from src.sync_processor import SyncProcessor


class TestSyncProcessor:
    """Test cases for SyncProcessor class."""

    def test_sync_processor_initialization(self, config):
        """Test SyncProcessor initialization."""
        processor = SyncProcessor(config)
        
        assert processor.config == config
        assert processor.file_watcher is not None
        assert processor.markdown_to_pdf is not None
        assert processor.pdf_to_markdown is not None
        assert processor.kindle_sync is not None
        
        # Check initial statistics
        assert processor.stats['files_processed'] == 0
        assert processor.stats['pdfs_generated'] == 0
        assert processor.stats['pdfs_sent_to_kindle'] == 0
        assert processor.stats['markdown_files_created'] == 0
        assert processor.stats['errors'] == 0

    def test_start_success(self, config):
        """Test successful sync processor start."""
        processor = SyncProcessor(config)
        
        # Mock validation and file watcher
        with patch.object(processor.config, 'validate', return_value=True):
            with patch.object(processor.file_watcher, 'start') as mock_start:
                result = processor.start()
                
                assert result is True
                mock_start.assert_called_once()

    def test_start_validation_failure(self, config):
        """Test sync processor start with validation failure."""
        processor = SyncProcessor(config)
        
        # Mock validation failure
        with patch.object(processor.config, 'validate', return_value=False):
            result = processor.start()
            
            assert result is False

    def test_start_file_watcher_error(self, config):
        """Test sync processor start with file watcher error."""
        processor = SyncProcessor(config)
        
        # Mock validation success but file watcher error
        with patch.object(processor.config, 'validate', return_value=True):
            with patch.object(processor.file_watcher, 'start', side_effect=Exception("Watcher error")):
                result = processor.start()
                
                assert result is False

    def test_stop_success(self, config):
        """Test successful sync processor stop."""
        processor = SyncProcessor(config)
        
        # Mock file watcher
        with patch.object(processor.file_watcher, 'stop') as mock_stop:
            processor.stop()
            
            mock_stop.assert_called_once()

    def test_stop_with_error(self, config):
        """Test sync processor stop with error."""
        processor = SyncProcessor(config)
        
        # Mock file watcher error
        with patch.object(processor.file_watcher, 'stop', side_effect=Exception("Stop error")):
            # Should not raise exception
            processor.stop()

    def test_process_file_markdown(self, config, temp_dir, sample_markdown_content):
        """Test processing a markdown file."""
        processor = SyncProcessor(config)
        
        # Create a markdown file
        md_file = temp_dir / "test.md"
        md_file.write_text(sample_markdown_content)
        
        # Mock the markdown processing
        with patch.object(processor, '_process_markdown_file') as mock_process:
            processor._process_file(md_file)
            
            mock_process.assert_called_once_with(md_file)
            assert processor.stats['files_processed'] == 1

    def test_process_file_pdf(self, config, temp_dir, sample_pdf_content):
        """Test processing a PDF file."""
        processor = SyncProcessor(config)
        
        # Create a PDF file
        pdf_file = temp_dir / "test.pdf"
        pdf_file.write_bytes(sample_pdf_content)
        
        # Mock the PDF processing
        with patch.object(processor, '_process_pdf_file') as mock_process:
            processor._process_file(pdf_file)
            
            mock_process.assert_called_once_with(pdf_file)
            assert processor.stats['files_processed'] == 1

    def test_process_file_unsupported_type(self, config, temp_dir):
        """Test processing an unsupported file type."""
        processor = SyncProcessor(config)
        
        # Create an unsupported file
        txt_file = temp_dir / "test.txt"
        txt_file.write_text("Text content")
        
        # Mock the processing methods
        with patch.object(processor, '_process_markdown_file') as mock_md:
            with patch.object(processor, '_process_pdf_file') as mock_pdf:
                processor._process_file(txt_file)
                
                # Neither method should be called
                mock_md.assert_not_called()
                mock_pdf.assert_not_called()
                assert processor.stats['files_processed'] == 0

    def test_process_file_error(self, config, temp_dir, sample_markdown_content):
        """Test processing a file with error."""
        processor = SyncProcessor(config)
        
        # Create a markdown file
        md_file = temp_dir / "test.md"
        md_file.write_text(sample_markdown_content)
        
        # Mock processing to raise exception
        with patch.object(processor, '_process_markdown_file', side_effect=Exception("Processing error")):
            processor._process_file(md_file)
            
            assert processor.stats['files_processed'] == 0
            assert processor.stats['errors'] == 1

    def test_process_markdown_file_success(self, config, temp_dir, sample_markdown_content):
        """Test successful markdown file processing."""
        processor = SyncProcessor(config)
        
        # Create a markdown file
        md_file = temp_dir / "test.md"
        md_file.write_text(sample_markdown_content)
        
        # Mock auto-convert enabled
        with patch.object(processor.config, 'get', return_value=True):
            with patch.object(processor.kindle_sync, 'backup_file') as mock_backup:
                with patch.object(processor.markdown_to_pdf, 'convert_markdown_to_pdf') as mock_convert:
                    with patch.object(processor.kindle_sync, 'send_pdf_to_kindle') as mock_send:
                        mock_convert.return_value = temp_dir / "test.pdf"
                        mock_send.return_value = True
                        
                        processor._process_markdown_file(md_file)
                        
                        # Verify all steps were called
                        mock_backup.assert_called_once_with(md_file)
                        mock_convert.assert_called_once_with(md_file)
                        mock_send.assert_called_once()
                        
                        # Verify statistics
                        assert processor.stats['pdfs_generated'] == 1
                        assert processor.stats['pdfs_sent_to_kindle'] == 1

    def test_process_markdown_file_auto_convert_disabled(self, config, temp_dir, sample_markdown_content):
        """Test markdown file processing with auto-convert disabled."""
        processor = SyncProcessor(config)
        
        # Create a markdown file
        md_file = temp_dir / "test.md"
        md_file.write_text(sample_markdown_content)
        
        # Mock auto-convert disabled
        with patch.object(processor.config, 'get', return_value=False):
            with patch.object(processor.kindle_sync, 'backup_file') as mock_backup:
                with patch.object(processor.markdown_to_pdf, 'convert_markdown_to_pdf') as mock_convert:
                    processor._process_markdown_file(md_file)
                    
                    # Backup should still be called
                    mock_backup.assert_called_once_with(md_file)
                    # Convert should not be called
                    mock_convert.assert_not_called()

    def test_process_markdown_file_send_failed(self, config, temp_dir, sample_markdown_content):
        """Test markdown file processing with send failure."""
        processor = SyncProcessor(config)
        
        # Create a markdown file
        md_file = temp_dir / "test.md"
        md_file.write_text(sample_markdown_content)
        
        # Mock auto-convert and auto-send enabled
        with patch.object(processor.config, 'get', side_effect=lambda key: True):
            with patch.object(processor.kindle_sync, 'backup_file'):
                with patch.object(processor.markdown_to_pdf, 'convert_markdown_to_pdf') as mock_convert:
                    with patch.object(processor.kindle_sync, 'send_pdf_to_kindle') as mock_send:
                        mock_convert.return_value = temp_dir / "test.pdf"
                        mock_send.return_value = False  # Send failed
                        
                        processor._process_markdown_file(md_file)
                        
                        # Verify statistics
                        assert processor.stats['pdfs_generated'] == 1
                        assert processor.stats['pdfs_sent_to_kindle'] == 0

    def test_process_markdown_file_auto_send_disabled(self, config, temp_dir, sample_markdown_content):
        """Test markdown file processing with auto-send disabled."""
        processor = SyncProcessor(config)
        
        # Create a markdown file
        md_file = temp_dir / "test.md"
        md_file.write_text(sample_markdown_content)
        
        # Mock auto-convert enabled but auto-send disabled
        def mock_get(key):
            if key == 'sync.auto_convert_on_save':
                return True
            elif key == 'sync.auto_send_to_kindle':
                return False
            return True
        
        with patch.object(processor.config, 'get', side_effect=mock_get):
            with patch.object(processor.kindle_sync, 'backup_file'):
                with patch.object(processor.markdown_to_pdf, 'convert_markdown_to_pdf') as mock_convert:
                    with patch.object(processor.kindle_sync, 'send_pdf_to_kindle') as mock_send:
                        mock_convert.return_value = temp_dir / "test.pdf"
                        
                        processor._process_markdown_file(md_file)
                        
                        # Convert should be called
                        mock_convert.assert_called_once()
                        # Send should not be called
                        mock_send.assert_not_called()
                        
                        # Verify statistics
                        assert processor.stats['pdfs_generated'] == 1
                        assert processor.stats['pdfs_sent_to_kindle'] == 0

    def test_process_pdf_file_success(self, config, temp_dir, sample_pdf_content):
        """Test successful PDF file processing."""
        processor = SyncProcessor(config)
        
        # Create a PDF file
        pdf_file = temp_dir / "test.pdf"
        pdf_file.write_bytes(sample_pdf_content)
        
        # Mock the PDF processing
        with patch.object(processor.kindle_sync, 'backup_file') as mock_backup:
            with patch.object(processor.pdf_to_markdown, 'convert_pdf_to_markdown') as mock_convert:
                mock_convert.return_value = temp_dir / "test.md"
                
                processor._process_pdf_file(pdf_file)
                
                # Verify all steps were called
                mock_backup.assert_called_once_with(pdf_file)
                mock_convert.assert_called_once_with(pdf_file)
                
                # Verify statistics
                assert processor.stats['markdown_files_created'] == 1

    def test_process_pdf_file_error(self, config, temp_dir, sample_pdf_content):
        """Test PDF file processing with error."""
        processor = SyncProcessor(config)
        
        # Create a PDF file
        pdf_file = temp_dir / "test.pdf"
        pdf_file.write_bytes(sample_pdf_content)
        
        # Mock processing to raise exception
        with patch.object(processor.kindle_sync, 'backup_file'):
            with patch.object(processor.pdf_to_markdown, 'convert_pdf_to_markdown', side_effect=Exception("Conversion error")):
                with pytest.raises(Exception, match="Conversion error"):
                    processor._process_pdf_file(pdf_file)

    def test_sync_from_kindle_success(self, config, temp_dir):
        """Test successful sync from Kindle."""
        processor = SyncProcessor(config)
        
        # Create mock synced files
        synced_files = [
            temp_dir / "doc1.pdf",
            temp_dir / "doc2.pdf"
        ]
        
        # Mock Kindle sync
        with patch.object(processor.kindle_sync, 'sync_from_kindle', return_value=synced_files):
            with patch.object(processor, '_process_pdf_file') as mock_process:
                result = processor.sync_from_kindle()
                
                assert result == 2
                assert mock_process.call_count == 2

    def test_sync_from_kindle_error(self, config):
        """Test sync from Kindle with error."""
        processor = SyncProcessor(config)
        
        # Mock Kindle sync to raise exception
        with patch.object(processor.kindle_sync, 'sync_from_kindle', side_effect=Exception("Sync error")):
            result = processor.sync_from_kindle()
            
            assert result == 0

    def test_sync_from_kindle_mixed_files(self, config, temp_dir):
        """Test sync from Kindle with mixed file types."""
        processor = SyncProcessor(config)
        
        # Create mock synced files (PDF and non-PDF)
        synced_files = [
            temp_dir / "doc1.pdf",
            temp_dir / "doc2.md"  # Non-PDF file
        ]
        
        # Mock Kindle sync
        with patch.object(processor.kindle_sync, 'sync_from_kindle', return_value=synced_files):
            with patch.object(processor, '_process_pdf_file') as mock_process:
                result = processor.sync_from_kindle()
                
                # Only PDF files should be processed
                assert result == 2  # Total synced files
                assert mock_process.call_count == 1  # Only PDF processed

    def test_get_statistics(self, config):
        """Test getting processing statistics."""
        processor = SyncProcessor(config)
        
        # Modify some statistics
        processor.stats['files_processed'] = 5
        processor.stats['errors'] = 1
        
        stats = processor.get_statistics()
        
        assert stats['files_processed'] == 5
        assert stats['errors'] == 1
        assert stats['pdfs_generated'] == 0  # Unchanged
        
        # Verify it's a copy, not the original
        stats['files_processed'] = 10
        assert processor.stats['files_processed'] == 5

    def test_reset_statistics(self, config):
        """Test resetting processing statistics."""
        processor = SyncProcessor(config)
        
        # Modify some statistics
        processor.stats['files_processed'] = 5
        processor.stats['errors'] = 1
        
        processor.reset_statistics()
        
        # Verify all statistics are reset
        assert processor.stats['files_processed'] == 0
        assert processor.stats['pdfs_generated'] == 0
        assert processor.stats['pdfs_sent_to_kindle'] == 0
        assert processor.stats['markdown_files_created'] == 0
        assert processor.stats['errors'] == 0

    def test_cleanup_old_files_success(self, config, temp_dir):
        """Test successful cleanup of old files."""
        processor = SyncProcessor(config)
        
        # Create mock folders
        sync_folder = temp_dir / "sync"
        backup_folder = temp_dir / "backup"
        sync_folder.mkdir()
        backup_folder.mkdir()
        
        # Mock config methods
        with patch.object(processor.config, 'get_sync_folder_path', return_value=sync_folder):
            with patch.object(processor.config, 'get_backup_folder_path', return_value=backup_folder):
                with patch.object(processor.kindle_sync, 'cleanup_old_files') as mock_cleanup:
                    mock_cleanup.return_value = 3  # 3 files cleaned from each folder
                    
                    result = processor.cleanup_old_files(max_age_days=30)
                    
                    assert result == 6  # 3 + 3
                    assert mock_cleanup.call_count == 2

    def test_cleanup_old_files_error(self, config, temp_dir):
        """Test cleanup with error."""
        processor = SyncProcessor(config)
        
        # Create mock folders
        sync_folder = temp_dir / "sync"
        backup_folder = temp_dir / "backup"
        sync_folder.mkdir()
        backup_folder.mkdir()
        
        # Mock config methods
        with patch.object(processor.config, 'get_sync_folder_path', return_value=sync_folder):
            with patch.object(processor.config, 'get_backup_folder_path', return_value=backup_folder):
                with patch.object(processor.kindle_sync, 'cleanup_old_files', side_effect=Exception("Cleanup error")):
                    result = processor.cleanup_old_files(max_age_days=30)
                    
                    assert result == 0

    def test_cleanup_old_files_folders_not_exist(self, config, temp_dir):
        """Test cleanup when folders don't exist."""
        processor = SyncProcessor(config)
        
        # Create non-existent folders
        sync_folder = temp_dir / "non_existent_sync"
        backup_folder = temp_dir / "non_existent_backup"
        
        # Mock config methods
        with patch.object(processor.config, 'get_sync_folder_path', return_value=sync_folder):
            with patch.object(processor.config, 'get_backup_folder_path', return_value=backup_folder):
                with patch.object(processor.kindle_sync, 'cleanup_old_files') as mock_cleanup:
                    result = processor.cleanup_old_files(max_age_days=30)
                    
                    # Should not call cleanup for non-existent folders
                    mock_cleanup.assert_not_called()
                    assert result == 0
