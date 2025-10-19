"""
Unit tests for file watcher functionality.

Tests the file system monitoring and event handling.
"""

import tempfile
import time
from unittest.mock import MagicMock, Mock, patch

import pytest
from pathlib import Path

from src.config import Config
from src.core.exceptions import ErrorSeverity, FileProcessingError
from src.file_watcher import ObsidianFileWatcher


class TestObsidianFileWatcher:
    """Test cases for ObsidianFileWatcher."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration."""
        config = Mock(spec=Config)
        config.get.side_effect = lambda key, default=None: {
            "obsidian.watch_subfolders": True,
            "advanced.debounce_time": 0.05,  # Very small for immediate processing in tests
            "patterns.markdown_files": "*.md",
            "patterns.pdf_files": "*.pdf",
        }.get(key, default)

        # Mock config methods
        config.get_obsidian_vault_path.return_value = Path("/tmp/test_vault")
        return config

    @pytest.fixture
    def temp_directory(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def mock_callback(self):
        """Create a mock callback function."""
        return Mock()

    @pytest.fixture
    def file_watcher(self, mock_config, mock_callback):
        """Create a ObsidianFileWatcher instance."""
        with patch("src.file_watcher.Observer"):
            return ObsidianFileWatcher(mock_config, mock_callback)

    def test_file_watcher_initialization(self, mock_config, mock_callback):
        """Test file watcher initialization."""
        with patch("src.file_watcher.Observer"):
            watcher = ObsidianFileWatcher(mock_config, mock_callback)
            assert watcher.config == mock_config
            assert watcher.callback == mock_callback
            assert watcher.observer is not None

    def test_start_watching_success(self, file_watcher, temp_directory):
        """Test successful start of file watching."""
        # Mock the vault path to use temp directory
        file_watcher.config.get_obsidian_vault_path.return_value = temp_directory

        # Mock observer methods
        file_watcher.observer.start.return_value = None
        file_watcher.observer.is_alive.return_value = True

        result = file_watcher.start()

        assert result is True
        file_watcher.observer.schedule.assert_called_once()
        file_watcher.observer.start.assert_called_once()

    def test_start_watching_vault_not_exists(self, file_watcher):
        """Test start watching when vault path doesn't exist."""
        # Mock non-existent vault path
        file_watcher.config.get_obsidian_vault_path.return_value = Path(
            "/non/existent/path"
        )

        result = file_watcher.start()

        assert result is False

    def test_start_watching_observer_error(self, file_watcher, temp_directory):
        """Test start watching with observer error."""
        # Mock the vault path
        file_watcher.config.get_obsidian_vault_path.return_value = temp_directory

        # Mock observer error
        file_watcher.observer.start.side_effect = Exception("Observer start failed")

        result = file_watcher.start()

        assert result is False

    def test_stop_watching_success(self, file_watcher):
        """Test successful stop of file watching."""
        # Mock observer methods
        file_watcher.observer.stop.return_value = None
        file_watcher.observer.join.return_value = None

        file_watcher.stop()

        file_watcher.observer.stop.assert_called_once()
        file_watcher.observer.join.assert_called_once()

    def test_stop_watching_observer_error(self, file_watcher):
        """Test stop watching with observer error."""
        # Mock observer error
        file_watcher.observer.stop.side_effect = Exception("Observer stop failed")

        # Should not raise exception
        file_watcher.stop()

    def test_is_alive_true(self, file_watcher):
        """Test is_alive returns True when observer is alive."""
        file_watcher.observer.is_alive.return_value = True

        assert file_watcher.is_alive() is True

    def test_is_alive_false(self, file_watcher):
        """Test is_alive returns False when observer is not alive."""
        file_watcher.observer.is_alive.return_value = False

        assert file_watcher.is_alive() is False

    def test_is_alive_observer_error(self, file_watcher):
        """Test is_alive handles observer error."""
        file_watcher.observer.is_alive.side_effect = Exception("Observer error")

        assert file_watcher.is_alive() is False

    def test_get_watched_paths(self, file_watcher, temp_directory):
        """Test getting watched paths."""
        # Mock the vault path
        file_watcher.config.get_obsidian_vault_path.return_value = temp_directory

        paths = file_watcher.get_watched_paths()

        assert len(paths) == 1
        assert paths[0] == str(temp_directory)

    def test_get_watched_paths_with_subfolders(self, file_watcher, temp_directory):
        """Test getting watched paths with subfolders."""
        # Create subdirectories
        subdir1 = temp_directory / "subdir1"
        subdir2 = temp_directory / "subdir2"
        subdir1.mkdir()
        subdir2.mkdir()

        # Mock the vault path
        file_watcher.config.get_obsidian_vault_path.return_value = temp_directory

        paths = file_watcher.get_watched_paths()

        # Should include main directory and subdirectories
        assert len(paths) >= 1
        assert str(temp_directory) in paths

    def test_handle_file_event_created(self, file_watcher, temp_directory):
        """Test handling file created event."""
        # Create the test file
        test_file = temp_directory / "test.md"
        test_file.write_text("# Test")
        
        # Mock event
        mock_event = Mock()
        mock_event.event_type = "created"
        mock_event.src_path = str(test_file)
        mock_event.is_directory = False

        # Mock file processor
        file_watcher.file_processor = Mock()

        file_watcher._handle_file_event(mock_event)

        # Should call file processor
        file_watcher.file_processor.process_file.assert_called_once()

    def test_handle_file_event_modified(self, file_watcher, temp_directory):
        """Test handling file modified event."""
        # Create the test file
        test_file = temp_directory / "test.md"
        test_file.write_text("# Test")
        
        # Mock event
        mock_event = Mock()
        mock_event.event_type = "modified"
        mock_event.src_path = str(test_file)
        mock_event.is_directory = False

        # Mock file processor
        file_watcher.file_processor = Mock()

        file_watcher._handle_file_event(mock_event)

        # Should call file processor
        file_watcher.file_processor.process_file.assert_called_once()

    def test_handle_file_event_moved(self, file_watcher, temp_directory):
        """Test handling file moved event."""
        # Create the test files
        old_file = temp_directory / "old.md"
        new_file = temp_directory / "new.md"
        old_file.write_text("# Old")
        new_file.write_text("# New")
        
        # Mock event
        mock_event = Mock()
        mock_event.event_type = "moved"
        mock_event.src_path = str(old_file)
        mock_event.dest_path = str(new_file)
        mock_event.is_directory = False

        # Mock file processor
        file_watcher.file_processor = Mock()

        file_watcher._handle_file_event(mock_event)

        # Should call file processor for both old and new paths
        assert file_watcher.file_processor.process_file.call_count == 2

    def test_handle_file_event_directory(self, file_watcher):
        """Test handling directory event (should be ignored)."""
        # Mock event
        mock_event = Mock()
        mock_event.event_type = "created"
        mock_event.src_path = "/tmp/test_vault/new_dir"
        mock_event.is_directory = True

        # Mock file processor
        file_watcher.file_processor = Mock()

        file_watcher._handle_file_event(mock_event)

        # Should not call file processor for directories
        file_watcher.file_processor.process_file.assert_not_called()

    def test_handle_file_event_unsupported_type(self, file_watcher):
        """Test handling unsupported file type event."""
        # Mock event
        mock_event = Mock()
        mock_event.event_type = "created"
        mock_event.src_path = "/tmp/test_vault/test.txt"
        mock_event.is_directory = False

        # Mock file processor
        file_watcher.file_processor = Mock()

        file_watcher._handle_file_event(mock_event)

        # Should not call file processor for unsupported types
        file_watcher.file_processor.process_file.assert_not_called()

    def test_handle_file_event_processor_error(self, file_watcher):
        """Test handling file event with processor error."""
        # Mock event
        mock_event = Mock()
        mock_event.event_type = "created"
        mock_event.src_path = "/tmp/test_vault/test.md"
        mock_event.is_directory = False

        # Mock file processor with error
        file_watcher.file_processor = Mock()
        file_watcher.file_processor.process_file.side_effect = Exception(
            "Processing failed"
        )

        # Should not raise exception
        file_watcher._handle_file_event(mock_event)

    def test_is_supported_file_type_markdown(self, file_watcher):
        """Test checking supported file type for markdown."""
        assert file_watcher._is_supported_file_type("test.md") is True
        assert file_watcher._is_supported_file_type("test.MD") is True

    def test_is_supported_file_type_pdf(self, file_watcher):
        """Test checking supported file type for PDF."""
        assert file_watcher._is_supported_file_type("test.pdf") is True
        assert file_watcher._is_supported_file_type("test.PDF") is True

    def test_is_supported_file_type_unsupported(self, file_watcher):
        """Test checking unsupported file types."""
        assert file_watcher._is_supported_file_type("test.txt") is False
        assert file_watcher._is_supported_file_type("test.doc") is False
        assert file_watcher._is_supported_file_type("test") is False

    def test_set_file_processor(self, file_watcher):
        """Test setting file processor."""
        mock_processor = Mock()

        file_watcher.set_file_processor(mock_processor)

        assert file_watcher.file_processor == mock_processor

    def test_get_statistics(self, file_watcher):
        """Test getting file watcher statistics."""
        stats = file_watcher.get_statistics()

        assert "events_processed" in stats
        assert "files_created" in stats
        assert "files_modified" in stats
        assert "files_moved" in stats
        assert "errors" in stats

    def test_reset_statistics(self, file_watcher):
        """Test resetting file watcher statistics."""
        # Process some events to generate statistics
        file_watcher.stats["events_processed"] = 10
        file_watcher.stats["files_created"] = 5

        file_watcher.reset_statistics()

        assert file_watcher.stats["events_processed"] == 0
        assert file_watcher.stats["files_created"] == 0

    def test_debounce_mechanism(self, file_watcher):
        """Test debounce mechanism for rapid file changes."""
        # Set a longer debounce time for this test
        file_watcher.debounce_time = 2.0
        
        # Mock event
        mock_event = Mock()
        mock_event.event_type = "modified"
        mock_event.src_path = "/tmp/test_vault/test.md"
        mock_event.is_directory = False

        # Mock file processor
        file_watcher.file_processor = Mock()

        # Process the same event multiple times rapidly
        for _ in range(5):
            file_watcher._handle_file_event(mock_event)

        # Should only process once due to debouncing
        assert file_watcher.file_processor.process_file.call_count <= 1
