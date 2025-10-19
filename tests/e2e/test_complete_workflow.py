"""End-to-end tests for complete Kindle Scribe sync workflows."""

import threading
import time
from unittest.mock import Mock, patch

import pytest
from pathlib import Path

from src.sync_processor import SyncProcessor


class TestCompleteWorkflow:
    """End-to-end tests for complete sync workflows."""

    @pytest.mark.e2e
    @pytest.mark.slow
    def test_complete_markdown_to_kindle_workflow(self, config, obsidian_vault):
        """Test complete workflow from markdown creation to Kindle delivery."""
        # Create sync folder
        sync_folder = obsidian_vault / "Kindle Sync"
        sync_folder.mkdir(exist_ok=True)

        # Create a test markdown document
        md_content = """# My Kindle Document

This is a test document that will be processed through the complete workflow.

## Features Tested

- Markdown to PDF conversion
- Email delivery to Kindle
- File backup
- Processing statistics

### Code Example

```python
def test_function():
    return "Hello, Kindle Scribe!"
```

## Conclusion

This document tests the complete automation workflow.
"""

        md_file = sync_folder / "workflow_test.md"
        md_file.write_text(md_content)

        # Initialize sync processor
        processor = SyncProcessor(config)

        # Mock external dependencies
        with patch.object(
            processor.markdown_to_pdf, "convert_markdown_to_pdf"
        ) as mock_convert_pdf:
            with patch.object(
                processor.kindle_sync, "send_pdf_to_kindle"
            ) as mock_send_to_kindle:
                with patch.object(processor.kindle_sync, "backup_file") as mock_backup:
                    # Mock successful operations
                    mock_backup.return_value = Path("/tmp/backup.md")
                    mock_convert_pdf.return_value = Path("/tmp/test.pdf")
                    mock_send_to_kindle.return_value = True

                    # Process the markdown file
                    processor._process_markdown_file(md_file)

                    # Verify all steps were executed
                    mock_backup.assert_called_once_with(md_file)
                    mock_convert_pdf.assert_called_once_with(md_file)
                    mock_send_to_kindle.assert_called_once()

                    # Verify statistics
                    assert processor.stats["pdfs_generated"] == 1
                    assert processor.stats["pdfs_sent_to_kindle"] == 1

    @pytest.mark.e2e
    @pytest.mark.slow
    def test_complete_pdf_to_obsidian_workflow(self, config, obsidian_vault):
        """Test complete workflow from PDF import to Obsidian markdown."""
        # Create sync folder
        sync_folder = obsidian_vault / "Kindle Sync"
        sync_folder.mkdir(exist_ok=True)

        # Create a test PDF file (simulated)
        pdf_file = sync_folder / "imported_document.pdf"
        pdf_file.write_bytes(b"Mock PDF content")

        # Initialize sync processor
        processor = SyncProcessor(config)

        # Mock PDF conversion dependencies
        with patch.object(
            processor.pdf_to_markdown, "convert_pdf_to_markdown"
        ) as mock_convert:
            with patch.object(processor.kindle_sync, "backup_file") as mock_backup:
                # Mock successful conversion
                mock_backup.return_value = Path("/tmp/backup.pdf")
                mock_convert.return_value = Path("/tmp/test.md")

                # Process the PDF file
                processor._process_pdf_file(pdf_file)

                # Verify all steps were executed
                mock_backup.assert_called_once_with(pdf_file)
                mock_convert.assert_called_once_with(pdf_file)

                # Verify statistics
                assert processor.stats["markdown_files_created"] == 1

    @pytest.mark.e2e
    @pytest.mark.slow
    def test_file_watcher_workflow(self, config, obsidian_vault):
        """Test complete file watcher workflow with real file operations."""
        # Create sync folder
        sync_folder = obsidian_vault / "Kindle Sync"
        sync_folder.mkdir(exist_ok=True)

        # Track processed files
        processed_files = []

        def file_callback(file_path):
            processed_files.append(file_path)

        # Initialize sync processor
        processor = SyncProcessor(config)
        processor.file_watcher = processor.file_watcher.__class__(config, file_callback)

        # Mock the observer
        with patch("watchdog.observers.Observer") as mock_observer_class:
            mock_observer = Mock()
            mock_observer_class.return_value = mock_observer

            # Start the processor
            processor.start()

            # Create test files
            md_file = sync_folder / "watched_document.md"
            md_file.write_text("# Watched Document\n\nThis file is being watched.")

            pdf_file = sync_folder / "watched_document.pdf"
            pdf_file.write_bytes(b"Watched PDF content")

            # Simulate file system events
            from watchdog.events import FileCreatedEvent

            md_event = FileCreatedEvent(str(md_file))
            pdf_event = FileCreatedEvent(str(pdf_file))

            # Process events
            processor.file_watcher.handler.on_created(md_event)
            processor.file_watcher.handler.on_created(pdf_event)

            # Wait for processing
            time.sleep(0.3)

            # Verify files were processed
            assert len(processed_files) == 2
            assert md_file in processed_files
            assert pdf_file in processed_files

            # Stop the processor
            processor.stop()

    @pytest.mark.e2e
    @pytest.mark.slow
    def test_concurrent_file_processing_workflow(self, config, obsidian_vault):
        """Test concurrent file processing workflow."""
        # Create sync folder
        sync_folder = obsidian_vault / "Kindle Sync"
        sync_folder.mkdir(exist_ok=True)

        # Create multiple test files
        test_files = []
        for i in range(10):
            md_file = sync_folder / f"concurrent_doc_{i}.md"
            md_file.write_text(
                f"# Concurrent Document {i}\n\nContent for document {i}."
            )
            test_files.append(md_file)

        # Initialize sync processor
        processor = SyncProcessor(config)

        # Track results
        results = []
        errors = []

        def process_file(file_path):
            try:
                with patch.object(
                    processor.markdown_to_pdf,
                    "convert_markdown_to_pdf",
                    return_value=Path("/tmp/test.pdf"),
                ):
                    with patch.object(
                        processor.kindle_sync, "send_pdf_to_kindle", return_value=True
                    ):
                        with patch.object(
                            processor.kindle_sync,
                            "backup_file",
                            return_value=Path("/tmp/backup.md"),
                        ):
                            processor._process_markdown_file(file_path)
                            results.append(file_path)
            except Exception as e:
                errors.append(e)

        # Process files concurrently
        threads = []
        for file_path in test_files:
            thread = threading.Thread(target=process_file, args=(file_path,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify all files were processed successfully
        assert len(results) == 10
        assert len(errors) == 0

        # Verify statistics
        assert processor.stats["pdfs_generated"] == 10
        assert processor.stats["pdfs_sent_to_kindle"] == 10

    @pytest.mark.e2e
    @pytest.mark.slow
    def test_error_recovery_workflow(self, config, obsidian_vault):
        """Test error recovery in complete workflow."""
        # Create sync folder
        sync_folder = obsidian_vault / "Kindle Sync"
        sync_folder.mkdir(exist_ok=True)

        # Create test files
        good_md_file = sync_folder / "good_document.md"
        good_md_file.write_text("# Good Document\n\nThis should process successfully.")

        bad_md_file = sync_folder / "bad_document.md"
        bad_md_file.write_text("# Bad Document\n\nThis will cause an error.")

        # Initialize sync processor
        processor = SyncProcessor(config)

        # Mock operations with mixed success/failure
        with patch.object(
            processor.markdown_to_pdf, "convert_markdown_to_pdf"
        ) as mock_convert:
            with patch.object(processor.kindle_sync, "send_pdf_to_kindle") as mock_send:
                with patch.object(processor.kindle_sync, "backup_file") as mock_backup:
                    # Configure mocks
                    def convert_side_effect(file_path):
                        if "bad" in str(file_path):
                            raise Exception("PDF generation failed")
                        return Path("/tmp/test.pdf")

                    def send_side_effect(*args, **kwargs):
                        return True

                    mock_convert.side_effect = convert_side_effect
                    mock_send.side_effect = send_side_effect
                    mock_backup.return_value = Path("/tmp/backup.md")

                    # Process good file
                    processor._process_markdown_file(good_md_file)

                    # Process bad file
                    with pytest.raises(Exception):
                        processor._process_markdown_file(bad_md_file)

                    # Verify statistics
                    assert processor.stats["pdfs_generated"] == 1
                    assert processor.stats["pdfs_sent_to_kindle"] == 1
                    assert (
                        processor.stats["errors"] == 0
                    )  # Error is raised, not counted

    @pytest.mark.e2e
    @pytest.mark.slow
    def test_backup_and_cleanup_workflow(self, config, obsidian_vault):
        """Test backup and cleanup workflow."""
        # Create sync folder
        sync_folder = obsidian_vault / "Kindle Sync"
        sync_folder.mkdir(exist_ok=True)

        # Create backup folder
        backup_folder = obsidian_vault.parent / "Backups"
        backup_folder.mkdir(exist_ok=True)

        # Create test files
        test_files = []
        for i in range(5):
            md_file = sync_folder / f"backup_test_{i}.md"
            md_file.write_text(f"# Backup Test {i}\n\nContent for backup test {i}.")
            test_files.append(md_file)

        # Initialize sync processor
        processor = SyncProcessor(config)

        # Mock backup operations
        with patch.object(processor.kindle_sync, "backup_file") as mock_backup:
            with patch.object(
                processor.markdown_to_pdf,
                "convert_markdown_to_pdf",
                return_value=Path("/tmp/test.pdf"),
            ):
                with patch.object(
                    processor.kindle_sync, "send_pdf_to_kindle", return_value=True
                ):
                    # Process files
                    for file_path in test_files:
                        processor._process_markdown_file(file_path)

                    # Verify backups were created
                    assert mock_backup.call_count == 5

                    # Test cleanup
                    with patch.object(
                        processor.kindle_sync, "cleanup_old_files"
                    ) as mock_cleanup:
                        with patch.object(
                            processor.config,
                            "get_backup_folder_path",
                            return_value=backup_folder,
                        ):
                            with patch.object(
                                processor.config,
                                "get_sync_folder_path",
                                return_value=sync_folder,
                            ):
                                # Mock returns 3 for each folder (sync and backup)
                                mock_cleanup.return_value = 3

                                cleaned_count = processor.cleanup_old_files(
                                    max_age_days=30
                                )

                                # Should be 3 + 3 = 6 total cleaned files
                                assert cleaned_count == 6
                                assert mock_cleanup.call_count == 2

    @pytest.mark.e2e
    @pytest.mark.slow
    def test_kindle_sync_workflow(self, config, obsidian_vault):
        """Test Kindle sync workflow."""
        # Create sync folder
        sync_folder = obsidian_vault / "Kindle Sync"
        sync_folder.mkdir(exist_ok=True)

        # Create mock Kindle documents
        kindle_docs_folder = obsidian_vault.parent / "kindle_docs"
        kindle_docs_folder.mkdir(exist_ok=True)

        kindle_pdf1 = kindle_docs_folder / "kindle_doc1.pdf"
        kindle_pdf2 = kindle_docs_folder / "kindle_doc2.pdf"
        kindle_pdf1.write_bytes(b"Kindle PDF 1 content")
        kindle_pdf2.write_bytes(b"Kindle PDF 2 content")

        # Initialize sync processor
        processor = SyncProcessor(config)

        # Mock Kindle sync operations
        with patch.object(processor.kindle_sync, "sync_from_kindle") as mock_sync:
            with patch.object(processor, "_process_pdf_file") as mock_process:
                # Configure mocks
                mock_sync.return_value = [
                    sync_folder / "kindle_doc1.pdf",
                    sync_folder / "kindle_doc2.pdf",
                ]

                # Sync from Kindle
                synced_count = processor.sync_from_kindle(kindle_docs_folder)

                # Verify sync operations
                assert synced_count == 2
                mock_sync.assert_called_once_with(kindle_docs_folder)
                assert mock_process.call_count == 2

    @pytest.mark.e2e
    @pytest.mark.slow
    def test_statistics_tracking_workflow(self, config, obsidian_vault):
        """Test statistics tracking throughout workflow."""
        # Create sync folder
        sync_folder = obsidian_vault / "Kindle Sync"
        sync_folder.mkdir(exist_ok=True)

        # Create test files
        md_file = sync_folder / "stats_test.md"
        md_file.write_text("# Statistics Test\n\nTesting statistics tracking.")

        pdf_file = sync_folder / "stats_test.pdf"
        pdf_file.write_bytes(b"Statistics test PDF content")

        # Initialize sync processor
        processor = SyncProcessor(config)

        # Mock operations
        with patch.object(
            processor.markdown_to_pdf,
            "convert_markdown_to_pdf",
            return_value=Path("/tmp/test.pdf"),
        ):
            with patch.object(
                processor.kindle_sync, "send_pdf_to_kindle", return_value=True
            ):
                with patch.object(
                    processor.kindle_sync,
                    "backup_file",
                    return_value=Path("/tmp/backup.md"),
                ):
                    with patch.object(
                        processor.pdf_to_markdown,
                        "convert_pdf_to_markdown",
                        return_value=Path("/tmp/test.md"),
                    ):
                        # Process markdown file
                        processor._process_markdown_file(md_file)

                        # Process PDF file
                        processor._process_pdf_file(pdf_file)

                        # Verify statistics
                        stats = processor.get_statistics()

                        assert (
                            stats["files_processed"] == 0
                        )  # Not incremented in _process_file
                        assert stats["pdfs_generated"] == 1
                        assert stats["pdfs_sent_to_kindle"] == 1
                        assert stats["markdown_files_created"] == 1
                        assert stats["errors"] == 0

                        # Test statistics reset
                        processor.reset_statistics()
                        reset_stats = processor.get_statistics()

                        assert reset_stats["files_processed"] == 0
                        assert reset_stats["pdfs_generated"] == 0
                        assert reset_stats["pdfs_sent_to_kindle"] == 0
                        assert reset_stats["markdown_files_created"] == 0
                        assert reset_stats["errors"] == 0

    @pytest.mark.e2e
    @pytest.mark.slow
    def test_configuration_validation_workflow(self, config, obsidian_vault):
        """Test configuration validation in workflow."""
        # Initialize sync processor
        processor = SyncProcessor(config)

        # Test with valid configuration
        with patch.object(processor.config, "validate", return_value=True):
            with patch.object(processor.file_watcher, "start"):
                result = processor.start()
                assert result is True

        # Test with invalid configuration
        with patch.object(processor.config, "validate", return_value=False):
            result = processor.start()
            assert result is False

    @pytest.mark.e2e
    @pytest.mark.slow
    def test_complete_system_lifecycle(self, config, obsidian_vault):
        """Test complete system lifecycle from start to stop."""
        # Create sync folder
        sync_folder = obsidian_vault / "Kindle Sync"
        sync_folder.mkdir(exist_ok=True)

        # Initialize sync processor
        processor = SyncProcessor(config)

        # Mock external dependencies
        with patch.object(processor.config, "validate", return_value=True):
            with patch.object(processor.file_watcher, "start") as mock_start:
                with patch.object(processor.file_watcher, "stop") as mock_stop:
                    with patch.object(
                        processor.file_watcher, "is_alive", return_value=True
                    ):
                        # Start the system
                        result = processor.start()
                        assert result is True
                        mock_start.assert_called_once()

                        # Create a test file during operation
                        md_file = sync_folder / "lifecycle_test.md"
                        md_file.write_text(
                            "# Lifecycle Test\n\nTesting system lifecycle."
                        )

                        # Simulate file processing
                        with patch.object(
                            processor.markdown_to_pdf,
                            "convert_markdown_to_pdf",
                            return_value=Path("/tmp/test.pdf"),
                        ):
                            with patch.object(
                                processor.kindle_sync,
                                "send_pdf_to_kindle",
                                return_value=True,
                            ):
                                with patch.object(
                                    processor.kindle_sync,
                                    "backup_file",
                                    return_value=Path("/tmp/backup.md"),
                                ):
                                    processor._process_markdown_file(md_file)

                        # Stop the system
                        processor.stop()
                        mock_stop.assert_called_once()

                        # Verify final statistics
                        stats = processor.get_statistics()
                        assert stats["pdfs_generated"] == 1
                        assert stats["pdfs_sent_to_kindle"] == 1
