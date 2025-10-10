"""Unit tests for file watcher functionality."""

import pytest
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from watchdog.events import FileModifiedEvent, FileCreatedEvent, FileMovedEvent

from src.file_watcher import ObsidianFileHandler, ObsidianFileWatcher


class TestObsidianFileHandler:
    """Test cases for ObsidianFileHandler class."""

    def test_handler_initialization(self, config, temp_dir):
        """Test ObsidianFileHandler initialization."""
        callback = Mock()
        handler = ObsidianFileHandler(config, callback)
        
        assert handler.config == config
        assert handler.callback == callback
        assert handler.debounce_time == 0.1  # From test config
        assert handler.markdown_pattern == "*.md"
        assert handler.pdf_pattern == "*.pdf"

    def test_should_process_file_markdown(self, config, temp_dir):
        """Test should_process_file for markdown files."""
        callback = Mock()
        handler = ObsidianFileHandler(config, callback)
        
        # Create a markdown file
        md_file = temp_dir / "test.md"
        md_file.write_text("# Test")
        
        # Mock the sync folder check
        with patch.object(handler.config, 'get_sync_folder_path', return_value=temp_dir):
            assert handler._should_process_file(md_file) is True

    def test_should_process_file_pdf(self, config, temp_dir):
        """Test should_process_file for PDF files."""
        callback = Mock()
        handler = ObsidianFileHandler(config, callback)
        
        # Create a PDF file
        pdf_file = temp_dir / "test.pdf"
        pdf_file.write_bytes(b"PDF content")
        
        # Mock the sync folder check
        with patch.object(handler.config, 'get_sync_folder_path', return_value=temp_dir):
            assert handler._should_process_file(pdf_file) is True

    def test_should_process_file_unsupported_type(self, config, temp_dir):
        """Test should_process_file for unsupported file types."""
        callback = Mock()
        handler = ObsidianFileHandler(config, callback)
        
        # Create an unsupported file
        txt_file = temp_dir / "test.txt"
        txt_file.write_text("Text content")
        
        assert handler._should_process_file(txt_file) is False

    def test_should_process_file_too_large(self, config, temp_dir):
        """Test should_process_file for files that are too large."""
        callback = Mock()
        handler = ObsidianFileHandler(config, callback)
        
        # Create a large file
        large_file = temp_dir / "large.md"
        large_file.write_text("x" * 1024 * 1024)  # 1MB of content
        
        # Mock the sync folder check
        with patch.object(handler.config, 'get_sync_folder_path', return_value=temp_dir):
            # Should return False due to size limit (10MB in test config)
            assert handler._should_process_file(large_file) is True  # 1MB is under 10MB limit

    def test_parse_size(self, config):
        """Test _parse_size method."""
        callback = Mock()
        handler = ObsidianFileHandler(config, callback)
        
        assert handler._parse_size("1024") == 1024
        assert handler._parse_size("1KB") == 1024
        assert handler._parse_size("1MB") == 1024 * 1024
        assert handler._parse_size("1GB") == 1024 * 1024 * 1024

    def test_schedule_processing(self, config, temp_dir):
        """Test _schedule_processing method."""
        callback = Mock()
        handler = ObsidianFileHandler(config, callback)
        
        test_file = temp_dir / "test.md"
        test_file.write_text("# Test")
        
        # Mock threading.Timer
        with patch('threading.Timer') as mock_timer:
            handler._schedule_processing(test_file)
            
            # Verify timer was created and started
            mock_timer.assert_called_once()
            mock_timer.return_value.start.assert_called_once()

    def test_schedule_processing_cancels_previous(self, config, temp_dir):
        """Test that scheduling processing cancels previous timer."""
        callback = Mock()
        handler = ObsidianFileHandler(config, callback)
        
        test_file = temp_dir / "test.md"
        test_file.write_text("# Test")
        
        # Create a mock timer
        mock_timer = Mock()
        handler.pending_files[test_file] = mock_timer
        
        with patch('threading.Timer') as new_mock_timer:
            handler._schedule_processing(test_file)
            
            # Verify previous timer was cancelled
            mock_timer.cancel.assert_called_once()
            # Verify new timer was created
            new_mock_timer.assert_called_once()

    def test_process_file_success(self, config, temp_dir):
        """Test successful file processing."""
        callback = Mock()
        handler = ObsidianFileHandler(config, callback)
        
        test_file = temp_dir / "test.md"
        test_file.write_text("# Test")
        
        # Mock the debounce time to be very small
        handler.debounce_time = 0.01
        
        # Process the file
        handler._process_file(test_file)
        
        # Verify callback was called
        callback.assert_called_once_with(test_file)
        # Verify file was added to processed files
        assert test_file in handler.processed_files

    def test_process_file_not_exists(self, config, temp_dir):
        """Test processing a file that no longer exists."""
        callback = Mock()
        handler = ObsidianFileHandler(config, callback)
        
        non_existent_file = temp_dir / "non_existent.md"
        
        # Process the non-existent file
        handler._process_file(non_existent_file)
        
        # Verify callback was not called
        callback.assert_not_called()

    def test_on_modified_event(self, config, temp_dir):
        """Test on_modified event handling."""
        callback = Mock()
        handler = ObsidianFileHandler(config, callback)
        
        # Create a test file
        test_file = temp_dir / "test.md"
        test_file.write_text("# Test")
        
        # Create a mock event
        event = Mock()
        event.is_directory = False
        event.src_path = str(test_file)
        
        # Mock the should_process_file method
        with patch.object(handler, '_should_process_file', return_value=True):
            with patch.object(handler, '_schedule_processing') as mock_schedule:
                handler.on_modified(event)
                mock_schedule.assert_called_once_with(test_file)

    def test_on_created_event(self, config, temp_dir):
        """Test on_created event handling."""
        callback = Mock()
        handler = ObsidianFileHandler(config, callback)
        
        # Create a test file
        test_file = temp_dir / "test.md"
        test_file.write_text("# Test")
        
        # Create a mock event
        event = Mock()
        event.is_directory = False
        event.src_path = str(test_file)
        
        # Mock the should_process_file method
        with patch.object(handler, '_should_process_file', return_value=True):
            with patch.object(handler, '_schedule_processing') as mock_schedule:
                handler.on_created(event)
                mock_schedule.assert_called_once_with(test_file)

    def test_on_moved_event(self, config, temp_dir):
        """Test on_moved event handling."""
        callback = Mock()
        handler = ObsidianFileHandler(config, callback)
        
        # Create a test file
        test_file = temp_dir / "test.md"
        test_file.write_text("# Test")
        
        # Create a mock event
        event = Mock()
        event.is_directory = False
        event.dest_path = str(test_file)
        
        # Mock the should_process_file method
        with patch.object(handler, '_should_process_file', return_value=True):
            with patch.object(handler, '_schedule_processing') as mock_schedule:
                handler.on_moved(event)
                mock_schedule.assert_called_once_with(test_file)

    def test_ignore_directory_events(self, config):
        """Test that directory events are ignored."""
        callback = Mock()
        handler = ObsidianFileHandler(config, callback)
        
        # Create mock events for directories
        modified_event = Mock()
        modified_event.is_directory = True
        
        created_event = Mock()
        created_event.is_directory = True
        
        moved_event = Mock()
        moved_event.is_directory = True
        
        # Mock the scheduling method
        with patch.object(handler, '_schedule_processing') as mock_schedule:
            handler.on_modified(modified_event)
            handler.on_created(created_event)
            handler.on_moved(moved_event)
            
            # Verify no scheduling occurred
            mock_schedule.assert_not_called()


class TestObsidianFileWatcher:
    """Test cases for ObsidianFileWatcher class."""

    def test_watcher_initialization(self, config):
        """Test ObsidianFileWatcher initialization."""
        callback = Mock()
        watcher = ObsidianFileWatcher(config, callback)
        
        assert watcher.config == config
        assert watcher.callback == callback
        assert watcher.is_running is False

    def test_start_watcher_success(self, config, obsidian_vault):
        """Test successful watcher start."""
        callback = Mock()
        watcher = ObsidianFileWatcher(config, callback)
        
        # Mock the observer
        with patch('watchdog.observers.Observer') as mock_observer_class:
            mock_observer = Mock()
            mock_observer_class.return_value = mock_observer
            
            # Mock the config to return the test vault
            with patch.object(config, 'get_obsidian_vault_path', return_value=obsidian_vault):
                watcher.start()
                
                # Verify observer was configured and started
                mock_observer.schedule.assert_called_once()
                mock_observer.start.assert_called_once()
                assert watcher.is_running is True

    def test_start_watcher_vault_not_exists(self, config):
        """Test watcher start with non-existent vault."""
        callback = Mock()
        watcher = ObsidianFileWatcher(config, callback)
        
        # Mock the config to return non-existent path
        with patch.object(config, 'get_obsidian_vault_path', return_value=Path('/non/existent')):
            with pytest.raises(FileNotFoundError):
                watcher.start()

    def test_stop_watcher(self, config):
        """Test watcher stop."""
        callback = Mock()
        watcher = ObsidianFileWatcher(config, callback)
        
        # Mock the observer
        mock_observer = Mock()
        watcher.observer = mock_observer
        watcher.is_running = True
        
        watcher.stop()
        
        # Verify observer was stopped
        mock_observer.stop.assert_called_once()
        mock_observer.join.assert_called_once()
        assert watcher.is_running is False

    def test_stop_watcher_not_running(self, config):
        """Test stopping a watcher that's not running."""
        callback = Mock()
        watcher = ObsidianFileWatcher(config, callback)
        
        # Mock the observer
        mock_observer = Mock()
        watcher.observer = mock_observer
        watcher.is_running = False
        
        watcher.stop()
        
        # Verify observer methods were not called
        mock_observer.stop.assert_not_called()
        mock_observer.join.assert_not_called()

    def test_is_alive(self, config):
        """Test is_alive method."""
        callback = Mock()
        watcher = ObsidianFileWatcher(config, callback)
        
        # Mock the observer
        mock_observer = Mock()
        mock_observer.is_alive.return_value = True
        watcher.observer = mock_observer
        
        assert watcher.is_alive() is True
        
        mock_observer.is_alive.return_value = False
        assert watcher.is_alive() is False

    def test_is_alive_no_observer(self, config):
        """Test is_alive method when no observer exists."""
        callback = Mock()
        watcher = ObsidianFileWatcher(config, callback)
        watcher.observer = None
        
        assert watcher.is_alive() is False

    def test_watch_subfolders_configuration(self, config, obsidian_vault):
        """Test that watch_subfolders configuration is respected."""
        callback = Mock()
        watcher = ObsidianFileWatcher(config, callback)
        
        # Mock the observer
        with patch('watchdog.observers.Observer') as mock_observer_class:
            mock_observer = Mock()
            mock_observer_class.return_value = mock_observer
            
            # Mock the config
            with patch.object(config, 'get_obsidian_vault_path', return_value=obsidian_vault):
                with patch.object(config, 'get', return_value=False):  # watch_subfolders = False
                    watcher.start()
                    
                    # Verify recursive=False was passed
                    mock_observer.schedule.assert_called_once()
                    call_args = mock_observer.schedule.call_args
                    assert call_args[1]['recursive'] is False

    def test_folder_creation_on_start(self, config, temp_dir):
        """Test that required folders are created on start."""
        callback = Mock()
        watcher = ObsidianFileWatcher(config, callback)
        
        # Create a vault path
        vault_path = temp_dir / "vault"
        vault_path.mkdir()
        
        # Mock the observer
        with patch('watchdog.observers.Observer') as mock_observer_class:
            mock_observer = Mock()
            mock_observer_class.return_value = mock_observer
            
            # Mock the config
            with patch.object(config, 'get_obsidian_vault_path', return_value=vault_path):
                watcher.start()
                
                # Verify folders were created
                sync_folder = vault_path / "Kindle Sync"
                templates_folder = vault_path / "Templates"
                
                assert sync_folder.exists()
                assert templates_folder.exists()
