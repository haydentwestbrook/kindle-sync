"""Unit tests for PDF conversion functionality."""

from pathlib import Path
from unittest.mock import Mock, mock_open, patch

import pytest

from src.pdf_converter import MarkdownToPDFConverter, PDFToMarkdownConverter


class TestMarkdownToPDFConverter:
    """Test cases for MarkdownToPDFConverter class."""

    def test_converter_initialization(self, config):
        """Test MarkdownToPDFConverter initialization."""
        converter = MarkdownToPDFConverter(config)

        assert converter.config == config
        assert converter.pdf_config == config.get_pdf_config()
        assert converter.markdown_config == config.get_markdown_config()
        assert converter.page_size is not None
        assert converter.margins is not None
        assert converter.styles is not None

    def test_setup_styles(self, config):
        """Test _setup_styles method."""
        converter = MarkdownToPDFConverter(config)
        styles = converter._setup_styles()

        # Check that required styles exist
        assert "Title" in styles
        assert "Heading1" in styles
        assert "Heading2" in styles
        assert "Heading3" in styles
        assert "BodyText" in styles
        assert "Code" in styles

        # Check style properties
        assert styles["Title"].fontSize == 18
        assert styles["Heading1"].fontSize == 16
        assert styles["BodyText"].fontSize == 12

    def test_convert_markdown_to_pdf_success(
        self, config, temp_dir, sample_markdown_content
    ):
        """Test successful markdown to PDF conversion."""
        converter = MarkdownToPDFConverter(config)

        # Create a markdown file
        md_file = temp_dir / "test.md"
        md_file.write_text(sample_markdown_content)

        # Mock the PDF generation
        with patch.object(converter, "_generate_pdf") as mock_generate:
            with patch.object(converter, "_process_markdown") as mock_process:
                mock_process.return_value = (
                    "<html><body>Processed content</body></html>"
                )

                result_path = converter.convert_markdown_to_pdf(md_file)

                # Verify the result
                expected_path = temp_dir / "test.pdf"
                assert result_path == expected_path

                # Verify methods were called
                mock_process.assert_called_once_with(sample_markdown_content)
                mock_generate.assert_called_once()

    def test_convert_markdown_to_pdf_custom_output(
        self, config, temp_dir, sample_markdown_content
    ):
        """Test markdown to PDF conversion with custom output path."""
        converter = MarkdownToPDFConverter(config)

        # Create a markdown file
        md_file = temp_dir / "test.md"
        md_file.write_text(sample_markdown_content)

        # Custom output path
        output_path = temp_dir / "custom_output.pdf"

        # Mock the PDF generation
        with patch.object(converter, "_generate_pdf") as mock_generate:
            with patch.object(converter, "_process_markdown") as mock_process:
                mock_process.return_value = (
                    "<html><body>Processed content</body></html>"
                )

                result_path = converter.convert_markdown_to_pdf(md_file, output_path)

                # Verify the result
                assert result_path == output_path

    def test_convert_markdown_to_pdf_file_not_found(self, config, temp_dir):
        """Test markdown to PDF conversion with non-existent file."""
        converter = MarkdownToPDFConverter(config)

        non_existent_file = temp_dir / "non_existent.md"

        with pytest.raises(FileNotFoundError):
            converter.convert_markdown_to_pdf(non_existent_file)

    def test_process_markdown(self, config):
        """Test _process_markdown method."""
        converter = MarkdownToPDFConverter(config)

        markdown_content = """# Test Document

This is a **bold** text and *italic* text.

## Code Example

```python
def hello():
    print("Hello, World!")
```

- Item 1
- Item 2
"""

        result = converter._process_markdown(markdown_content)

        # Verify HTML structure
        assert "<html>" in result
        assert "<head>" in result
        assert "<body>" in result
        assert "<style>" in result
        assert "Test Document" in result
        assert "bold" in result
        assert "italic" in result

    def test_generate_pdf_weasyprint_success(self, config):
        """Test PDF generation using WeasyPrint."""
        converter = MarkdownToPDFConverter(config)

        html_content = "<html><body><h1>Test</h1></body></html>"
        output_path = Path("/tmp/test.pdf")

        # Mock WeasyPrint
        with patch("weasyprint.HTML") as mock_html_class:
            mock_html = Mock()
            mock_html.write_pdf.return_value = b"PDF content"
            mock_html_class.return_value = mock_html

            with patch("builtins.open", mock_open()) as mock_file:
                converter._generate_pdf(html_content, output_path)

                # Verify WeasyPrint was used
                mock_html_class.assert_called_once_with(string=html_content)
                mock_html.write_pdf.assert_called_once()
                mock_file.assert_called_once_with(output_path, "wb")

    def test_generate_pdf_weasyprint_fallback(self, config):
        """Test PDF generation fallback to ReportLab when WeasyPrint fails."""
        converter = MarkdownToPDFConverter(config)

        html_content = "<html><body><h1>Test</h1></body></html>"
        output_path = Path("/tmp/test.pdf")

        # Mock WeasyPrint to fail
        with patch("weasyprint.HTML", side_effect=Exception("WeasyPrint error")):
            with patch.object(converter, "_generate_pdf_reportlab") as mock_reportlab:
                converter._generate_pdf(html_content, output_path)

                # Verify fallback was called
                mock_reportlab.assert_called_once_with(html_content, output_path)

    def test_generate_pdf_reportlab(self, config):
        """Test PDF generation using ReportLab."""
        converter = MarkdownToPDFConverter(config)

        html_content = "<html><body><h1>Test</h1><p>Test paragraph</p></body></html>"
        output_path = Path("/tmp/test.pdf")

        # Mock ReportLab components
        with patch("src.pdf_converter.SimpleDocTemplate") as mock_doc_class:
            with patch.object(converter, "_parse_html_to_reportlab") as mock_parse:
                mock_doc = Mock()
                mock_doc_class.return_value = mock_doc
                mock_parse.return_value = [Mock(), Mock()]

                converter._generate_pdf_reportlab(html_content, output_path)

                # Verify ReportLab was used
                mock_doc_class.assert_called_once()
                mock_parse.assert_called_once_with(html_content)
                mock_doc.build.assert_called_once()

    def test_parse_html_to_reportlab(self, config):
        """Test HTML to ReportLab elements parsing."""
        converter = MarkdownToPDFConverter(config)

        html_content = """<h1>Title</h1>
<h2>Heading 2</h2>
<h3>Heading 3</h3>
<p>This is a paragraph.</p>
<br>
<p>Another paragraph.</p>"""

        elements = converter._parse_html_to_reportlab(html_content)

        # Verify elements were created
        assert len(elements) > 0
        # All elements should be ReportLab elements
        for element in elements:
            assert hasattr(element, "wrap") or hasattr(element, "drawOn")

    def test_page_size_configuration(self, temp_dir):
        """Test different page size configurations."""
        # Test A4 configuration
        config_a4 = Mock()
        config_a4.get_pdf_config.return_value = {"page_size": "A4"}
        config_a4.get_markdown_config.return_value = {}

        converter_a4 = MarkdownToPDFConverter(config_a4)
        assert converter_a4.page_size[0] == 595.2755905511812  # A4 width in points

        # Test Letter configuration
        config_letter = Mock()
        config_letter.get_pdf_config.return_value = {"page_size": "Letter"}
        config_letter.get_markdown_config.return_value = {}

        converter_letter = MarkdownToPDFConverter(config_letter)
        assert converter_letter.page_size[0] == 612.0  # Letter width in points

    def test_margins_configuration(self, temp_dir):
        """Test margins configuration."""
        config_custom = Mock()
        config_custom.get_pdf_config.return_value = {
            "page_size": "A4",
            "margins": [36, 36, 36, 36],  # 0.5 inch margins
        }
        config_custom.get_markdown_config.return_value = {}

        converter = MarkdownToPDFConverter(config_custom)

        # Verify margins were converted correctly (points to inches)
        # 36 points * (1 inch / 72 points) = 0.5 inches
        expected_margin = 36 * (1 / 72)  # 36 points to inches
        assert converter.margins[0] == expected_margin


class TestPDFToMarkdownConverter:
    """Test cases for PDFToMarkdownConverter class."""

    def test_converter_initialization(self, config):
        """Test PDFToMarkdownConverter initialization."""
        converter = PDFToMarkdownConverter(config)

        assert converter.config == config
        assert converter.ocr_config == config.get_ocr_config()

    def test_convert_pdf_to_markdown_success(
        self, config, temp_dir, sample_pdf_content
    ):
        """Test successful PDF to markdown conversion."""
        converter = PDFToMarkdownConverter(config)

        # Create a PDF file
        pdf_file = temp_dir / "test.pdf"
        pdf_file.write_bytes(sample_pdf_content)

        # Mock OCR dependencies
        with patch("pdf2image.convert_from_path") as mock_convert:
            with patch("pytesseract.image_to_string") as mock_ocr:
                mock_convert.return_value = [Mock()]  # Mock image
                mock_ocr.return_value = "Extracted text from OCR"

                result_path = converter.convert_pdf_to_markdown(pdf_file)

                # Verify the result
                expected_path = temp_dir / "test.md"
                assert result_path == expected_path

                # Verify the markdown file was created
                assert expected_path.exists()
                content = expected_path.read_text()
                assert "Extracted text from OCR" in content

    def test_convert_pdf_to_markdown_custom_output(
        self, config, temp_dir, sample_pdf_content
    ):
        """Test PDF to markdown conversion with custom output path."""
        converter = PDFToMarkdownConverter(config)

        # Create a PDF file
        pdf_file = temp_dir / "test.pdf"
        pdf_file.write_bytes(sample_pdf_content)

        # Custom output path
        output_path = temp_dir / "custom_output.md"

        # Mock OCR dependencies
        with patch("pdf2image.convert_from_path") as mock_convert:
            with patch("pytesseract.image_to_string") as mock_ocr:
                mock_convert.return_value = [Mock()]
                mock_ocr.return_value = "Extracted text"

                result_path = converter.convert_pdf_to_markdown(pdf_file, output_path)

                # Verify the result
                assert result_path == output_path

    def test_convert_pdf_to_markdown_missing_dependencies(
        self, config, temp_dir, sample_pdf_content
    ):
        """Test PDF to markdown conversion with missing OCR dependencies."""
        converter = PDFToMarkdownConverter(config)

        # Create a PDF file
        pdf_file = temp_dir / "test.pdf"
        pdf_file.write_bytes(sample_pdf_content)

        # Mock ImportError for missing dependencies
        with patch("pdf2image.convert_from_path", side_effect=ImportError):
            with pytest.raises(ImportError):
                converter.convert_pdf_to_markdown(pdf_file)

    def test_convert_pdf_to_markdown_multiple_pages(
        self, config, temp_dir, sample_pdf_content
    ):
        """Test PDF to markdown conversion with multiple pages."""
        converter = PDFToMarkdownConverter(config)

        # Create a PDF file
        pdf_file = temp_dir / "test.pdf"
        pdf_file.write_bytes(sample_pdf_content)

        # Mock multiple pages
        mock_images = [Mock(), Mock(), Mock()]

        with patch("pdf2image.convert_from_path") as mock_convert:
            with patch("pytesseract.image_to_string") as mock_ocr:
                mock_convert.return_value = mock_images
                mock_ocr.side_effect = ["Page 1 text", "Page 2 text", "Page 3 text"]

                result_path = converter.convert_pdf_to_markdown(pdf_file)

                # Verify OCR was called for each page
                assert mock_ocr.call_count == 3

                # Verify the markdown file contains all pages
                content = result_path.read_text()
                assert "Page 1 text" in content
                assert "Page 2 text" in content
                assert "Page 3 text" in content

    def test_process_extracted_text(self, config):
        """Test _process_extracted_text method."""
        converter = PDFToMarkdownConverter(config)

        extracted_text = """TITLE IN CAPS
This is a regular paragraph with some text.

SHORT HEADING
Another paragraph with more content.

This is a very long paragraph that should not be converted to a heading because it's too long and ends with a period."""

        result = converter._process_extracted_text(extracted_text)
        lines = result.split("\n")

        # Verify heading detection
        assert lines[0] == "# TITLE IN CAPS"
        assert lines[1] == "This is a regular paragraph with some text."
        assert lines[3] == "# SHORT HEADING"
        assert lines[4] == "Another paragraph with more content."
        assert (
            lines[6]
            == "This is a very long paragraph that should not be converted to a heading because it's too long and ends with a period."
        )

    def test_ocr_configuration(self, config, temp_dir, sample_pdf_content):
        """Test OCR configuration usage."""
        converter = PDFToMarkdownConverter(config)

        # Create a PDF file
        pdf_file = temp_dir / "test.pdf"
        pdf_file.write_bytes(sample_pdf_content)

        # Mock OCR with custom configuration
        with patch("pdf2image.convert_from_path") as mock_convert:
            with patch("pytesseract.image_to_string") as mock_ocr:
                mock_convert.return_value = [Mock()]
                mock_ocr.return_value = "Extracted text"

                converter.convert_pdf_to_markdown(pdf_file)

                # Verify OCR was called with correct configuration
                mock_ocr.assert_called_once()
                call_args = mock_ocr.call_args
                assert call_args[1]["lang"] == "eng"  # From test config
                assert "--psm 6" in call_args[1]["config"]

    def test_convert_pdf_to_markdown_file_not_found(self, config, temp_dir):
        """Test PDF to markdown conversion with non-existent file."""
        converter = PDFToMarkdownConverter(config)

        non_existent_file = temp_dir / "non_existent.pdf"

        # Mock pdf2image to raise FileNotFoundError
        with patch("pdf2image.convert_from_path") as mock_convert:
            mock_convert.side_effect = FileNotFoundError("File not found")

            with pytest.raises(FileNotFoundError):
                converter.convert_pdf_to_markdown(non_existent_file)

    def test_convert_pdf_to_markdown_empty_pdf(self, config, temp_dir):
        """Test PDF to markdown conversion with empty PDF."""
        converter = PDFToMarkdownConverter(config)

        # Create an empty PDF file
        pdf_file = temp_dir / "empty.pdf"
        pdf_file.write_bytes(b"")

        # Mock OCR to return empty result
        with patch("pdf2image.convert_from_path") as mock_convert:
            with patch("pytesseract.image_to_string") as mock_ocr:
                mock_convert.return_value = []
                mock_ocr.return_value = ""

                result_path = converter.convert_pdf_to_markdown(pdf_file)

                # Verify empty markdown file was created
                assert result_path.exists()
                content = result_path.read_text()
                assert content.strip() == ""
