"""
Unit tests for PDF converter functionality.

Tests the PDF conversion between Markdown and PDF formats.
"""

import tempfile
from unittest.mock import Mock, mock_open, patch

import pytest
from pathlib import Path

from src.config import Config
from src.core.exceptions import ErrorSeverity, FileProcessingError
from src.pdf_converter import MarkdownToPDFConverter, PDFToMarkdownConverter


class TestMarkdownToPDFConverter:
    """Test cases for MarkdownToPDFConverter."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration."""
        config = Mock(spec=Config)
        config.get.side_effect = lambda key, default=None: {
            "processing.pdf.page_size": "A4",
            "processing.pdf.margins": [72, 72, 72, 72],
            "processing.pdf.font_family": "Times-Roman",
            "processing.pdf.font_size": 12,
            "processing.pdf.line_spacing": 1.2,
            "processing.markdown.extensions": ["tables", "fenced_code", "toc"],
            "processing.markdown.preserve_links": True,
        }.get(key, default)
        return config

    @pytest.fixture
    def converter(self, mock_config):
        """Create a MarkdownToPDFConverter instance."""
        return MarkdownToPDFConverter(mock_config)

    @pytest.fixture
    def temp_markdown_file(self):
        """Create a temporary markdown file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(
                "# Test Document\n\nThis is a test document.\n\n## Section 1\n\nSome content here.\n"
            )
            temp_path = Path(f.name)

        yield temp_path
        temp_path.unlink(missing_ok=True)

    def test_converter_initialization(self, mock_config):
        """Test converter initialization."""
        converter = MarkdownToPDFConverter(mock_config)
        assert converter.config == mock_config

    @patch("src.pdf_converter.weasyprint.HTML")
    @patch("src.pdf_converter.markdown.markdown")
    def test_convert_markdown_to_pdf_success(
        self, mock_markdown, mock_html, converter, temp_markdown_file
    ):
        """Test successful markdown to PDF conversion."""
        # Mock markdown conversion
        mock_markdown.return_value = (
            "<h1>Test Document</h1><p>This is a test document.</p>"
        )

        # Mock HTML to PDF conversion
        mock_html_instance = Mock()
        mock_html.return_value = mock_html_instance
        mock_html_instance.write_pdf.return_value = b"PDF content"

        result = converter.convert_markdown_to_pdf(temp_markdown_file)

        assert result is not None
        assert result.suffix == ".pdf"
        assert result.exists()

        # Verify markdown was called
        mock_markdown.assert_called_once()
        mock_html.assert_called_once()
        mock_html_instance.write_pdf.assert_called_once()

    @patch("src.pdf_converter.weasyprint.HTML")
    @patch("src.pdf_converter.markdown.markdown")
    def test_convert_markdown_to_pdf_with_custom_output(
        self, mock_markdown, mock_html, converter, temp_markdown_file
    ):
        """Test markdown to PDF conversion with custom output path."""
        custom_output = temp_markdown_file.parent / "custom_output.pdf"

        # Mock conversions
        mock_markdown.return_value = "<h1>Test Document</h1>"
        mock_html_instance = Mock()
        mock_html.return_value = mock_html_instance
        mock_html_instance.write_pdf.return_value = b"PDF content"

        result = converter.convert_markdown_to_pdf(temp_markdown_file, custom_output)

        assert result == custom_output
        assert result.exists()

    @patch("src.pdf_converter.weasyprint.HTML")
    @patch("src.pdf_converter.markdown.markdown")
    def test_convert_markdown_to_pdf_conversion_error(
        self, mock_markdown, mock_html, converter, temp_markdown_file
    ):
        """Test markdown to PDF conversion with conversion error."""
        # Mock markdown conversion
        mock_markdown.return_value = "<h1>Test Document</h1>"

        # Mock HTML conversion error
        mock_html.side_effect = Exception("Conversion failed")

        with pytest.raises(FileProcessingError) as exc_info:
            converter.convert_markdown_to_pdf(temp_markdown_file)

        assert exc_info.value.severity == ErrorSeverity.MEDIUM
        assert "Failed to convert markdown to PDF" in str(exc_info.value)

    def test_convert_markdown_to_pdf_file_not_found(self, converter):
        """Test markdown to PDF conversion with non-existent file."""
        non_existent_file = Path("/non/existent/file.md")

        with pytest.raises(FileProcessingError) as exc_info:
            converter.convert_markdown_to_pdf(non_existent_file)

        assert exc_info.value.severity == ErrorSeverity.HIGH
        assert "Input file does not exist" in str(exc_info.value)

    @patch("src.pdf_converter.weasyprint.HTML")
    @patch("src.pdf_converter.markdown.markdown")
    def test_convert_markdown_to_pdf_pdf_generation_error(
        self, mock_markdown, mock_html, converter, temp_markdown_file
    ):
        """Test markdown to PDF conversion with PDF generation error."""
        # Mock markdown conversion
        mock_markdown.return_value = "<h1>Test Document</h1>"

        # Mock HTML instance with PDF generation error
        mock_html_instance = Mock()
        mock_html.return_value = mock_html_instance
        mock_html_instance.write_pdf.side_effect = Exception("PDF generation failed")

        with pytest.raises(FileProcessingError) as exc_info:
            converter.convert_markdown_to_pdf(temp_markdown_file)

        assert exc_info.value.severity == ErrorSeverity.MEDIUM
        assert "Failed to generate PDF" in str(exc_info.value)

    def test_get_pdf_config(self, converter):
        """Test getting PDF configuration."""
        config = converter._get_pdf_config()

        assert config["page_size"] == "A4"
        assert config["margins"] == [72, 72, 72, 72]
        assert config["font_family"] == "Times-Roman"
        assert config["font_size"] == 12
        assert config["line_spacing"] == 1.2

    def test_get_markdown_config(self, converter):
        """Test getting markdown configuration."""
        config = converter._get_markdown_config()

        assert "tables" in config["extensions"]
        assert "fenced_code" in config["extensions"]
        assert "toc" in config["extensions"]
        assert config["preserve_links"] is True


class TestPDFToMarkdownConverter:
    """Test cases for PDFToMarkdownConverter."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration."""
        config = Mock(spec=Config)
        config.get.side_effect = lambda key, default=None: {
            "processing.ocr.language": "eng",
            "processing.ocr.confidence_threshold": 60,
        }.get(key, default)
        return config

    @pytest.fixture
    def converter(self, mock_config):
        """Create a PDFToMarkdownConverter instance."""
        return PDFToMarkdownConverter(mock_config)

    @pytest.fixture
    def temp_pdf_file(self):
        """Create a temporary PDF file."""
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".pdf", delete=False) as f:
            # Write a minimal PDF header
            f.write(b"%PDF-1.4\n")
            f.write(b"1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n")
            f.write(b"2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n")
            f.write(
                b"3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n>>\nendobj\n"
            )
            f.write(
                b"xref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n"
            )
            f.write(b"trailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n174\n%%EOF\n")
            temp_path = Path(f.name)

        yield temp_path
        temp_path.unlink(missing_ok=True)

    def test_converter_initialization(self, mock_config):
        """Test converter initialization."""
        converter = PDFToMarkdownConverter(mock_config)
        assert converter.config == mock_config

    @patch("src.pdf_converter.pdf2image.convert_from_path")
    @patch("src.pdf_converter.pytesseract.image_to_string")
    def test_convert_pdf_to_markdown_success(
        self, mock_ocr, mock_convert, converter, temp_pdf_file
    ):
        """Test successful PDF to markdown conversion."""
        # Mock PDF to image conversion
        mock_image = Mock()
        mock_convert.return_value = [mock_image]

        # Mock OCR
        mock_ocr.return_value = "Test Document\n\nThis is a test document.\n\nSection 1\n\nSome content here."

        result = converter.convert_pdf_to_markdown(temp_pdf_file)

        assert result is not None
        assert result.suffix == ".md"
        assert result.exists()

        # Verify OCR was called
        mock_convert.assert_called_once()
        mock_ocr.assert_called_once()

    @patch("src.pdf_converter.pdf2image.convert_from_path")
    @patch("src.pdf_converter.pytesseract.image_to_string")
    def test_convert_pdf_to_markdown_with_custom_output(
        self, mock_ocr, mock_convert, converter, temp_pdf_file
    ):
        """Test PDF to markdown conversion with custom output path."""
        custom_output = temp_pdf_file.parent / "custom_output.md"

        # Mock conversions
        mock_image = Mock()
        mock_convert.return_value = [mock_image]
        mock_ocr.return_value = "Test Document\n\nThis is a test document."

        result = converter.convert_pdf_to_markdown(temp_pdf_file, custom_output)

        assert result == custom_output
        assert result.exists()

    @patch("src.pdf_converter.pdf2image.convert_from_path")
    def test_convert_pdf_to_markdown_conversion_error(
        self, mock_convert, converter, temp_pdf_file
    ):
        """Test PDF to markdown conversion with conversion error."""
        # Mock conversion error
        mock_convert.side_effect = Exception("PDF conversion failed")

        with pytest.raises(FileProcessingError) as exc_info:
            converter.convert_pdf_to_markdown(temp_pdf_file)

        assert exc_info.value.severity == ErrorSeverity.MEDIUM
        assert "Failed to convert PDF to images" in str(exc_info.value)

    def test_convert_pdf_to_markdown_file_not_found(self, converter):
        """Test PDF to markdown conversion with non-existent file."""
        non_existent_file = Path("/non/existent/file.pdf")

        with pytest.raises(FileProcessingError) as exc_info:
            converter.convert_pdf_to_markdown(non_existent_file)

        assert exc_info.value.severity == ErrorSeverity.HIGH
        assert "Input file does not exist" in str(exc_info.value)

    @patch("src.pdf_converter.pdf2image.convert_from_path")
    @patch("src.pdf_converter.pytesseract.image_to_string")
    def test_convert_pdf_to_markdown_ocr_error(
        self, mock_ocr, mock_convert, converter, temp_pdf_file
    ):
        """Test PDF to markdown conversion with OCR error."""
        # Mock PDF to image conversion
        mock_image = Mock()
        mock_convert.return_value = [mock_image]

        # Mock OCR error
        mock_ocr.side_effect = Exception("OCR failed")

        with pytest.raises(FileProcessingError) as exc_info:
            converter.convert_pdf_to_markdown(temp_pdf_file)

        assert exc_info.value.severity == ErrorSeverity.MEDIUM
        assert "Failed to extract text from PDF" in str(exc_info.value)

    def test_get_ocr_config(self, converter):
        """Test getting OCR configuration."""
        config = converter._get_ocr_config()

        assert config["language"] == "eng"
        assert config["confidence_threshold"] == 60

    @patch("src.pdf_converter.pdf2image.convert_from_path")
    @patch("src.pdf_converter.pytesseract.image_to_string")
    def test_convert_pdf_to_markdown_empty_text(
        self, mock_ocr, mock_convert, converter, temp_pdf_file
    ):
        """Test PDF to markdown conversion with empty OCR result."""
        # Mock PDF to image conversion
        mock_image = Mock()
        mock_convert.return_value = [mock_image]

        # Mock empty OCR result
        mock_ocr.return_value = ""

        result = converter.convert_pdf_to_markdown(temp_pdf_file)

        assert result is not None
        assert result.exists()

        # Check that the file contains a placeholder message
        content = result.read_text()
        assert "No text could be extracted" in content or len(content.strip()) == 0
