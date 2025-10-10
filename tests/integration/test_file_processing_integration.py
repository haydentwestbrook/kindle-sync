"""Integration tests for file processing workflows."""

import time
from unittest.mock import Mock, patch

import pytest
from src.file_watcher import ObsidianFileWatcher
from src.kindle_sync import KindleSync
from src.pdf_converter import MarkdownToPDFConverter, PDFToMarkdownConverter


class TestFileProcessingIntegration:
    """Integration tests for file processing workflows."""

    def test_markdown_to_pdf_workflow(self, config, temp_dir, sample_markdown_content):
        """Test complete markdown to PDF conversion workflow."""
        # Create markdown file
        md_file = temp_dir / "test_document.md"
        md_file.write_text(sample_markdown_content)

        # Initialize converter
        converter = MarkdownToPDFConverter(config)

        # Mock WeasyPrint for reliable testing
        with patch("weasyprint.HTML") as mock_html_class:
            mock_html = Mock()
            mock_html.write_pdf.return_value = b"Mock PDF content"
            mock_html_class.return_value = mock_html

            # Convert markdown to PDF
            pdf_path = converter.convert_markdown_to_pdf(md_file)

            # Verify conversion
            assert pdf_path.exists()
            assert pdf_path.suffix == ".pdf"
            assert pdf_path.name == "test_document.pdf"

            # Verify WeasyPrint was called
            mock_html_class.assert_called_once()
            mock_html.write_pdf.assert_called_once()

    def test_pdf_to_markdown_workflow(self, config, temp_dir, sample_pdf_content):
        """Test complete PDF to markdown conversion workflow."""
        # Create PDF file
        pdf_file = temp_dir / "test_document.pdf"
        pdf_file.write_bytes(sample_pdf_content)

        # Initialize converter
        converter = PDFToMarkdownConverter(config)

        # Mock OCR dependencies
        with patch("pdf2image.convert_from_path") as mock_convert:
            with patch("pytesseract.image_to_string") as mock_ocr:
                mock_convert.return_value = [Mock()]  # Mock image
                mock_ocr.return_value = "Extracted text from OCR processing"

                # Convert PDF to markdown
                md_path = converter.convert_pdf_to_markdown(pdf_file)

                # Verify conversion
                assert md_path.exists()
                assert md_path.suffix == ".md"
                assert md_path.name == "test_document.md"

                # Verify content
                content = md_path.read_text()
                assert "Extracted text from OCR processing" in content

                # Verify OCR was called
                mock_convert.assert_called_once_with(pdf_file)
                mock_ocr.assert_called_once()

    def test_file_watcher_integration(self, config, obsidian_vault):
        """Test file watcher integration with real file operations."""
        # Create sync folder
        sync_folder = obsidian_vault / "Kindle Sync"
        sync_folder.mkdir(exist_ok=True)

        # Track processed files (use set to avoid duplicates)
        processed_files = set()

        def file_callback(file_path):
            processed_files.add(file_path)

        # Initialize file watcher
        watcher = ObsidianFileWatcher(config, file_callback)

        # Mock the observer to avoid actual file system watching
        with patch("watchdog.observers.Observer") as mock_observer_class:
            mock_observer = Mock()
            mock_observer_class.return_value = mock_observer

            # Mock the config to return the test vault path
            with patch.object(config, 'get_obsidian_vault_path', return_value=obsidian_vault):
                # Start watcher
                watcher.start()

            # Create test files
            md_file = sync_folder / "test.md"
            md_file.write_text("# Test Document")

            pdf_file = sync_folder / "test.pdf"
            pdf_file.write_bytes(b"PDF content")

            # Simulate file events
            from watchdog.events import FileCreatedEvent

            md_event = FileCreatedEvent(str(md_file))
            pdf_event = FileCreatedEvent(str(pdf_file))

            # Process events
            watcher.handler.on_created(md_event)
            watcher.handler.on_created(pdf_event)

            # Wait for processing (debounce time)
            time.sleep(0.2)

            # Verify files were processed
            assert len(processed_files) == 2
            assert md_file in processed_files
            assert pdf_file in processed_files

            # Stop watcher
            watcher.stop()

    def test_kindle_sync_integration(self, config, temp_dir, sample_pdf_content):
        """Test Kindle sync integration with real file operations."""
        # Create test files
        pdf_file = temp_dir / "test_document.pdf"
        pdf_file.write_bytes(sample_pdf_content)

        # Initialize Kindle sync
        kindle_sync = KindleSync(config)

        # Test backup functionality
        backup_folder = temp_dir / "backups"
        backup_folder.mkdir()

        with patch.object(
            kindle_sync.config,
            "get_sync_config",
            return_value={
                "backup_originals": True,
                "backup_folder": str(backup_folder),
            },
        ):
            backup_path = kindle_sync.backup_file(pdf_file)

            # Verify backup was created
            assert backup_path is not None
            assert backup_path.exists()
            assert backup_path.read_bytes() == sample_pdf_content
            assert "test_document_" in backup_path.name

    def test_end_to_end_markdown_workflow(
        self, config, temp_dir, sample_markdown_content
    ):
        """Test end-to-end markdown processing workflow."""
        # Create markdown file
        md_file = temp_dir / "workflow_test.md"
        md_file.write_text(sample_markdown_content)

        # Initialize components
        pdf_converter = MarkdownToPDFConverter(config)
        kindle_sync = KindleSync(config)

        # Step 1: Convert markdown to PDF
        with patch("weasyprint.HTML") as mock_html_class:
            mock_html = Mock()
            mock_html.write_pdf.return_value = b"Generated PDF content"
            mock_html_class.return_value = mock_html

            pdf_path = pdf_converter.convert_markdown_to_pdf(md_file)

            # Verify PDF was created
            assert pdf_path.exists()
            assert pdf_path.suffix == ".pdf"

        # Step 2: Backup the original file
        backup_folder = temp_dir / "backups"
        backup_folder.mkdir()

        with patch.object(
            kindle_sync.config,
            "get_sync_config",
            return_value={
                "backup_originals": True,
                "backup_folder": str(backup_folder),
            },
        ):
            backup_path = kindle_sync.backup_file(md_file)

            # Verify backup was created
            assert backup_path is not None
            assert backup_path.exists()

        # Step 3: Send PDF to Kindle (mocked)
        with patch.object(kindle_sync, "_send_email") as mock_send:
            result = kindle_sync.send_pdf_to_kindle(pdf_path)

            # Verify email was sent
            assert result is True
            mock_send.assert_called_once()

    def test_end_to_end_pdf_workflow(self, config, temp_dir, sample_pdf_content):
        """Test end-to-end PDF processing workflow."""
        # Create PDF file
        pdf_file = temp_dir / "workflow_test.pdf"
        pdf_file.write_bytes(sample_pdf_content)

        # Initialize components
        pdf_converter = PDFToMarkdownConverter(config)
        kindle_sync = KindleSync(config)

        # Step 1: Backup the original file
        backup_folder = temp_dir / "backups"
        backup_folder.mkdir()

        with patch.object(
            kindle_sync.config,
            "get_sync_config",
            return_value={
                "backup_originals": True,
                "backup_folder": str(backup_folder),
            },
        ):
            backup_path = kindle_sync.backup_file(pdf_file)

            # Verify backup was created
            assert backup_path is not None
            assert backup_path.exists()

        # Step 2: Convert PDF to markdown
        with patch("pdf2image.convert_from_path") as mock_convert:
            with patch("pytesseract.image_to_string") as mock_ocr:
                mock_convert.return_value = [Mock()]
                mock_ocr.return_value = "Extracted text from PDF workflow test"

                md_path = pdf_converter.convert_pdf_to_markdown(pdf_file)

                # Verify markdown was created
                assert md_path.exists()
                assert md_path.suffix == ".md"

                # Verify content
                content = md_path.read_text()
                assert "Extracted text from PDF workflow test" in content

    def test_file_processing_with_large_files(self, config, temp_dir):
        """Test file processing with large files."""
        # Create a large markdown file
        large_content = "# Large Document\n\n" + "This is a test paragraph. " * 1000
        large_md_file = temp_dir / "large_document.md"
        large_md_file.write_text(large_content)

        # Initialize converter
        pdf_converter = MarkdownToPDFConverter(config)

        # Mock WeasyPrint
        with patch("weasyprint.HTML") as mock_html_class:
            mock_html = Mock()
            mock_html.write_pdf.return_value = b"Large PDF content"
            mock_html_class.return_value = mock_html

            # Convert large markdown to PDF
            pdf_path = pdf_converter.convert_markdown_to_pdf(large_md_file)

            # Verify conversion succeeded
            assert pdf_path.exists()
            assert pdf_path.suffix == ".pdf"

            # Verify WeasyPrint was called with large content
            mock_html_class.assert_called_once()
            call_args = mock_html_class.call_args[1]
            assert "Large Document" in call_args["string"]
            assert "This is a test paragraph" in call_args["string"]

    def test_file_processing_with_special_characters(self, config, temp_dir):
        """Test file processing with special characters and Unicode."""
        # Create markdown file with special characters
        special_content = """# Special Characters Test

## Unicode Content
- English: Hello, World!
- Chinese: 你好，世界！
- Japanese: こんにちは、世界！
- Arabic: مرحبا بالعالم!
- Emoji: 🚀📚💻

## Special Characters
- Quotes: "double" and 'single'
- Symbols: @#$%^&*()
- Math: α + β = γ
- Currency: €£¥$

## Code Example
```python
def hello_world():
    print("Hello, 世界! 🌍")
```
"""

        special_md_file = temp_dir / "special_chars.md"
        special_md_file.write_text(special_content, encoding="utf-8")

        # Initialize converter
        pdf_converter = MarkdownToPDFConverter(config)

        # Mock WeasyPrint
        with patch("weasyprint.HTML") as mock_html_class:
            mock_html = Mock()
            mock_html.write_pdf.return_value = b"Special chars PDF content"
            mock_html_class.return_value = mock_html

            # Convert special characters markdown to PDF
            pdf_path = pdf_converter.convert_markdown_to_pdf(special_md_file)

            # Verify conversion succeeded
            assert pdf_path.exists()
            assert pdf_path.suffix == ".pdf"

            # Verify special characters were processed
            call_args = mock_html_class.call_args[1]
            assert "你好，世界！" in call_args["string"]
            assert "こんにちは、世界！" in call_args["string"]
            assert "🚀📚💻" in call_args["string"]

    def test_concurrent_file_processing(self, config, temp_dir):
        """Test concurrent file processing."""
        import threading
        import time

        # Create multiple test files
        test_files = []
        for i in range(5):
            md_file = temp_dir / f"concurrent_test_{i}.md"
            md_file.write_text(f"# Test Document {i}\n\nContent for document {i}.")
            test_files.append(md_file)

        # Initialize converter
        pdf_converter = MarkdownToPDFConverter(config)

        # Track results
        results = []
        errors = []

        def process_file(file_path):
            try:
                with patch("weasyprint.HTML") as mock_html_class:
                    mock_html = Mock()
                    mock_html.write_pdf.return_value = (
                        f"PDF content for {file_path.name}".encode()
                    )
                    mock_html_class.return_value = mock_html

                    pdf_path = pdf_converter.convert_markdown_to_pdf(file_path)
                    results.append(pdf_path)
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
        assert len(results) == 5
        assert len(errors) == 0

        # Verify all PDF files were created
        for i, pdf_path in enumerate(results):
            assert pdf_path.exists()
            assert pdf_path.suffix == ".pdf"
            # Check that the PDF file corresponds to one of our test files
            assert any(f"concurrent_test_{j}" in pdf_path.name for j in range(5))

    def test_file_processing_error_recovery(self, config, temp_dir):
        """Test file processing error recovery."""
        # Create a test file
        md_file = temp_dir / "error_test.md"
        md_file.write_text("# Error Test Document")

        # Initialize converter
        pdf_converter = MarkdownToPDFConverter(config)

        # Test WeasyPrint failure with ReportLab fallback
        with patch("weasyprint.HTML", side_effect=Exception("WeasyPrint error")):
            with patch.object(
                pdf_converter, "_generate_pdf_reportlab"
            ) as mock_reportlab:
                # Make the mock create a real file
                def mock_generate_pdf_reportlab(html_content, output_path):
                    output_path.write_bytes(b"Mock PDF content")
                    return output_path
                
                mock_reportlab.side_effect = mock_generate_pdf_reportlab
                
                pdf_path = pdf_converter.convert_markdown_to_pdf(md_file)

                # Verify fallback was used
                mock_reportlab.assert_called_once()
                assert pdf_path.exists()
                assert pdf_path.suffix == ".pdf"
