"""Mock objects and factories for testing."""

from pathlib import Path
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, MagicMock
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import tempfile
import shutil

from .sample_data import SampleData


class MockFactory:
    """Factory for creating mock objects."""
    
    @staticmethod
    def create_mock_config(**overrides) -> Mock:
        """Create a mock Config object."""
        config = Mock()
        
        # Default configuration
        default_config = SampleData.get_sample_config(**overrides)
        
        # Configure mock methods
        config.get.side_effect = lambda key, default=None: _get_nested_value(default_config, key, default)
        config.get_obsidian_vault_path.return_value = Path(default_config['obsidian']['vault_path'])
        config.get_sync_folder_path.return_value = Path(default_config['obsidian']['vault_path']) / default_config['obsidian']['sync_folder']
        config.get_templates_folder_path.return_value = Path(default_config['obsidian']['vault_path']) / default_config['obsidian']['templates_folder']
        config.get_backup_folder_path.return_value = Path(default_config['sync']['backup_folder'])
        config.get_kindle_email.return_value = default_config['kindle']['email']
        config.get_approved_senders.return_value = default_config['kindle']['approved_senders']
        config.get_smtp_config.return_value = {
            'server': default_config['kindle']['smtp_server'],
            'port': default_config['kindle']['smtp_port'],
            'username': default_config['kindle']['smtp_username'],
            'password': default_config['kindle']['smtp_password']
        }
        config.get_ocr_config.return_value = default_config['processing']['ocr']
        config.get_pdf_config.return_value = default_config['processing']['pdf']
        config.get_markdown_config.return_value = default_config['processing']['markdown']
        config.get_sync_config.return_value = default_config['sync']
        config.get_patterns.return_value = default_config['patterns']
        config.get_logging_config.return_value = default_config['logging']
        config.get_advanced_config.return_value = default_config['advanced']
        config.validate.return_value = True
        
        return config

    @staticmethod
    def create_mock_file_system_event(event_type: str = "created", file_path: str = "/tmp/test.md", is_directory: bool = False) -> Mock:
        """Create a mock file system event."""
        event = Mock()
        event.event_type = event_type
        event.src_path = file_path
        event.dest_path = file_path.replace('.md', '_moved.md')
        event.is_directory = is_directory
        return event

    @staticmethod
    def create_mock_smtp_server() -> Mock:
        """Create a mock SMTP server."""
        server = Mock()
        server.starttls = Mock()
        server.login = Mock()
        server.sendmail = Mock()
        server.quit = Mock()
        return server

    @staticmethod
    def create_mock_email_message(subject: str = "Test Subject", to: str = "test@kindle.com", attachment_path: Optional[Path] = None) -> MIMEMultipart:
        """Create a mock email message."""
        msg = MIMEMultipart()
        msg['From'] = "test@gmail.com"
        msg['To'] = to
        msg['Subject'] = subject
        
        # Add body
        body = f"Please find attached: {attachment_path.name if attachment_path else 'document.pdf'}"
        msg.attach(MIMEText(body, 'plain'))
        
        # Add attachment if provided
        if attachment_path and attachment_path.exists():
            with open(attachment_path, 'rb') as f:
                attachment = MIMEApplication(f.read(), _subtype='pdf')
                attachment.add_header('Content-Disposition', 'attachment', filename=attachment_path.name)
                msg.attach(attachment)
        
        return msg

    @staticmethod
    def create_mock_pdf_converter() -> Mock:
        """Create a mock PDF converter."""
        converter = Mock()
        converter.convert_markdown_to_pdf.return_value = Path("/tmp/test.pdf")
        converter.convert_pdf_to_markdown.return_value = Path("/tmp/test.md")
        converter._generate_pdf = Mock()
        converter._process_markdown = Mock(return_value="<html><body>Processed content</body></html>")
        return converter

    @staticmethod
    def create_mock_kindle_sync() -> Mock:
        """Create a mock Kindle sync object."""
        kindle_sync = Mock()
        kindle_sync.send_pdf_to_kindle.return_value = True
        kindle_sync.copy_to_kindle_usb.return_value = True
        kindle_sync.backup_file.return_value = Path("/tmp/backup.pdf")
        kindle_sync.get_kindle_documents.return_value = []
        kindle_sync.sync_from_kindle.return_value = []
        kindle_sync.cleanup_old_files.return_value = 0
        kindle_sync._send_email = Mock()
        return kindle_sync

    @staticmethod
    def create_mock_file_watcher() -> Mock:
        """Create a mock file watcher."""
        watcher = Mock()
        watcher.start = Mock()
        watcher.stop = Mock()
        watcher.is_alive.return_value = True
        watcher.handler = Mock()
        watcher.handler._should_process_file = Mock(return_value=True)
        watcher.handler._schedule_processing = Mock()
        watcher.handler.on_created = Mock()
        watcher.handler.on_modified = Mock()
        watcher.handler.on_moved = Mock()
        return watcher

    @staticmethod
    def create_mock_sync_processor() -> Mock:
        """Create a mock sync processor."""
        processor = Mock()
        processor.start.return_value = True
        processor.stop = Mock()
        processor._process_file = Mock()
        processor._process_markdown_file = Mock()
        processor._process_pdf_file = Mock()
        processor.sync_from_kindle.return_value = 0
        processor.get_statistics.return_value = SampleData.get_sample_statistics()
        processor.reset_statistics = Mock()
        processor.cleanup_old_files.return_value = 0
        processor.file_watcher = MockFactory.create_mock_file_watcher()
        processor.markdown_to_pdf = MockFactory.create_mock_pdf_converter()
        processor.pdf_to_markdown = MockFactory.create_mock_pdf_converter()
        processor.kindle_sync = MockFactory.create_mock_kindle_sync()
        return processor

    @staticmethod
    def create_mock_ocr_result(text: str = "Extracted text", confidence: float = 85.0, language: str = "eng") -> Dict[str, Any]:
        """Create a mock OCR result."""
        return {
            "text": text,
            "confidence": confidence,
            "language": language
        }

    @staticmethod
    def create_mock_pdf_images(count: int = 1) -> List[Mock]:
        """Create mock PDF images."""
        images = []
        for i in range(count):
            image = Mock()
            image.size = (100, 100)
            image.mode = 'RGB'
            images.append(image)
        return images

    @staticmethod
    def create_mock_weasyprint() -> Mock:
        """Create a mock WeasyPrint object."""
        mock_html = Mock()
        mock_html.write_pdf.return_value = b"Mock PDF content"
        
        mock_weasyprint = Mock()
        mock_weasyprint.HTML.return_value = mock_html
        
        return mock_weasyprint

    @staticmethod
    def create_mock_reportlab() -> Mock:
        """Create a mock ReportLab object."""
        mock_doc = Mock()
        mock_doc.build = Mock()
        
        mock_simple_doc = Mock()
        mock_simple_doc.return_value = mock_doc
        
        return mock_simple_doc

    @staticmethod
    def create_mock_pytesseract() -> Mock:
        """Create a mock pytesseract object."""
        mock_tesseract = Mock()
        mock_tesseract.image_to_string.return_value = "Extracted text from OCR"
        return mock_tesseract

    @staticmethod
    def create_mock_pdf2image() -> Mock:
        """Create a mock pdf2image object."""
        mock_pdf2image = Mock()
        mock_pdf2image.convert_from_path.return_value = MockFactory.create_mock_pdf_images()
        return mock_pdf2image


class TemporaryFileManager:
    """Manager for temporary files during testing."""
    
    def __init__(self):
        self.temp_dir = None
        self.created_files = []
    
    def __enter__(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="kindle_sync_test_"))
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.temp_dir and self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_file(self, name: str, content: str = "", binary: bool = False) -> Path:
        """Create a temporary file."""
        file_path = self.temp_dir / name
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        if binary:
            file_path.write_bytes(content.encode() if isinstance(content, str) else content)
        else:
            file_path.write_text(content)
        
        self.created_files.append(file_path)
        return file_path
    
    def create_directory(self, name: str) -> Path:
        """Create a temporary directory."""
        dir_path = self.temp_dir / name
        dir_path.mkdir(parents=True, exist_ok=True)
        return dir_path
    
    def get_path(self, name: str = "") -> Path:
        """Get a path within the temporary directory."""
        return self.temp_dir / name if name else self.temp_dir


class MockDataGenerator:
    """Generator for mock data."""
    
    @staticmethod
    def generate_markdown_content(title: str = "Test Document", paragraphs: int = 3) -> str:
        """Generate mock markdown content."""
        content = f"# {title}\n\n"
        
        for i in range(paragraphs):
            content += f"This is paragraph {i + 1} of the test document. "
            content += "It contains some sample text to test the markdown processing functionality. "
            content += "The content includes various formatting options and special characters.\n\n"
        
        content += "## Code Example\n\n```python\ndef test_function():\n    return 'Hello, World!'\n```\n\n"
        content += "## List Items\n\n- Item 1\n- Item 2\n- Item 3\n\n"
        content += "**Bold text** and *italic text* and `inline code`.\n"
        
        return content
    
    @staticmethod
    def generate_pdf_content(size: int = 1024) -> bytes:
        """Generate mock PDF content."""
        # Simple PDF header
        header = b"%PDF-1.4\n"
        content = b"Mock PDF content for testing. " * (size // 30)
        return header + content
    
    @staticmethod
    def generate_file_tree(base_path: Path, structure: Dict[str, Any]) -> Dict[str, Path]:
        """Generate a file tree structure."""
        created_paths = {}
        
        def create_structure(current_structure: Dict[str, Any], current_path: Path):
            for name, content in current_structure.items():
                item_path = current_path / name
                if isinstance(content, dict):
                    item_path.mkdir(parents=True, exist_ok=True)
                    created_paths[name] = item_path
                    create_structure(content, item_path)
                else:
                    item_path.write_text(content)
                    created_paths[name] = item_path
        
        create_structure(structure, base_path)
        return created_paths


def _get_nested_value(data: Dict[str, Any], key: str, default: Any = None) -> Any:
    """Get a nested value from a dictionary using dot notation."""
    keys = key.split('.')
    value = data
    
    try:
        for k in keys:
            value = value[k]
        return value
    except (KeyError, TypeError):
        return default
