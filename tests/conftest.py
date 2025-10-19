"""Pytest configuration and shared fixtures."""

import sys

from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import shutil  # noqa: E402
import tempfile  # noqa: E402
from typing import Any  # noqa: E402
from collections.abc import Generator
from unittest.mock import Mock  # noqa: E402

import pytest  # noqa: E402
import yaml  # noqa: E402
from loguru import logger  # noqa: E402

from src.config import Config  # noqa: E402


@pytest.fixture(scope="session")
def test_data_dir() -> Path:
    """Create a temporary directory for test data."""
    temp_dir = Path(tempfile.mkdtemp(prefix="kindle_sync_test_"))
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for each test."""
    temp_dir = Path(tempfile.mkdtemp(prefix="kindle_sync_test_"))
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def sample_config(obsidian_vault: Path) -> dict[str, Any]:
    """Sample configuration for testing."""
    return {
        "obsidian": {
            "vault_path": str(obsidian_vault),
            "sync_folder": "Kindle Sync",
            "templates_folder": "Templates",
            "watch_subfolders": True,
        },
        "kindle": {
            "email": "test@kindle.com",
            "approved_senders": ["test@example.com"],
        },
        "smtp": {
            "host": "smtp.gmail.com",
            "port": 587,
            "username": "test@gmail.com",
            "password": "test_password",
            "use_tls": True,
        },
        "processing": {
            "ocr": {"language": "eng", "confidence_threshold": 60},
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
        },
        "sync": {
            "auto_convert_on_save": True,
            "auto_send_to_kindle": True,
            "backup_originals": True,
            "backup_folder": "Backups",
        },
        "patterns": {
            "markdown_files": "*.md",
            "pdf_files": "*.pdf",
            "image_files": "*.{png,jpg,jpeg}",
        },
        "logging": {
            "level": "DEBUG",
            "file": "test.log",
            "max_size": "1MB",
            "backup_count": 2,
        },
        "advanced": {
            "debounce_time": 0.1,
            "max_file_size": "10MB",
            "concurrent_processing": False,
            "retry_attempts": 1,
        },
    }


@pytest.fixture
def config_file(temp_dir: Path, sample_config: dict[str, Any]) -> Path:
    """Create a temporary config file for testing."""
    config_path = temp_dir / "test_config.yaml"
    with open(config_path, "w") as f:
        yaml.dump(sample_config, f)
    return config_path


@pytest.fixture
def config(config_file: Path) -> Config:
    """Create a Config instance for testing."""
    return Config(str(config_file))


@pytest.fixture
def obsidian_vault(temp_dir: Path) -> Path:
    """Create a mock Obsidian vault structure."""
    vault_path = temp_dir / "obsidian_vault"
    vault_path.mkdir()

    # Create sync folder
    sync_folder = vault_path / "Kindle Sync"
    sync_folder.mkdir()

    # Create templates folder
    templates_folder = vault_path / "Templates"
    templates_folder.mkdir()

    # Create backup folder
    backup_folder = temp_dir / "Backups"
    backup_folder.mkdir()

    return vault_path


@pytest.fixture
def sample_markdown_content() -> str:
    """Sample markdown content for testing."""
    return """# Test Document

This is a test document for the Kindle Scribe sync system.

## Features

- Automated file watching
- PDF conversion
- Email integration

### Code Example

```python
def hello_world():
    print("Hello, Kindle Scribe!")
```

## Conclusion

This system enables seamless sync between Kindle Scribe and Obsidian.
"""


@pytest.fixture
def sample_pdf_content() -> bytes:
    """Sample PDF content for testing (minimal valid PDF)."""
    return b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj

2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj

3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj

4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
72 720 Td
(Hello World) Tj
ET
endstream
endobj

xref
0 5
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000204 00000 n
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
297
%%EOF"""


@pytest.fixture
def mock_smtp_server():
    """Mock SMTP server for testing email functionality."""
    mock_server = Mock()
    mock_server.starttls = Mock()
    mock_server.login = Mock()
    mock_server.sendmail = Mock()
    mock_server.quit = Mock()
    return mock_server


@pytest.fixture
def mock_file_system_event():
    """Mock file system event for testing."""
    event = Mock()
    event.is_directory = False
    event.src_path = "/tmp/test_file.md"
    event.dest_path = "/tmp/test_file_moved.md"
    return event


@pytest.fixture
def mock_ocr_result():
    """Mock OCR result for testing."""
    return {
        "text": "This is extracted text from OCR",
        "confidence": 85.5,
        "language": "eng",
    }


@pytest.fixture
def mock_pdf_images():
    """Mock PDF to images conversion result."""
    import io

    from PIL import Image

    # Create a simple test image
    img = Image.new("RGB", (100, 100), color="white")
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="PNG")
    img_bytes.seek(0)

    return [Image.open(img_bytes)]


@pytest.fixture(autouse=True)
def setup_test_logging():
    """Set up test logging configuration."""
    # Remove existing loggers
    logger.remove()

    # Add test logger
    logger.add(
        "tests/test.log",
        level="DEBUG",
        format=(
            "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | "
            "{name}:{function}:{line} - {message}"
        ),
        rotation="1 MB",
        retention="1 day",
    )


@pytest.fixture
def mock_kindle_device():
    """Mock Kindle device for testing."""
    device = Mock()
    device.documents_path = Path("/tmp/kindle_documents")
    device.documents_path.mkdir(exist_ok=True)
    return device


@pytest.fixture
def sample_file_tree(temp_dir: Path) -> dict[str, Path]:
    """Create a sample file tree for testing."""
    files = {}

    # Create markdown files
    md_file = temp_dir / "test_document.md"
    md_file.write_text("# Test Document\n\nThis is a test.")
    files["markdown"] = md_file

    # Create PDF file
    pdf_file = temp_dir / "test_document.pdf"
    pdf_file.write_bytes(b"PDF content")
    files["pdf"] = pdf_file

    # Create image file
    img_file = temp_dir / "test_image.png"
    img_file.write_bytes(b"PNG content")
    files["image"] = img_file

    return files


@pytest.fixture
def mock_weasyprint():
    """Mock WeasyPrint for testing PDF generation."""
    mock_html = Mock()
    mock_html.write_pdf.return_value = b"Mock PDF content"

    mock_weasyprint = Mock()
    mock_weasyprint.HTML.return_value = mock_html

    return mock_weasyprint


@pytest.fixture
def mock_reportlab():
    """Mock ReportLab for testing PDF generation."""
    mock_doc = Mock()
    mock_doc.build = Mock()

    mock_simple_doc = Mock()
    mock_simple_doc.return_value = mock_doc

    return mock_simple_doc


# Test markers
def pytest_configure(config):
    """Configure custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "e2e: End-to-end tests")
    config.addinivalue_line("markers", "slow: Slow running tests")
    config.addinivalue_line("markers", "docker: Tests requiring Docker")
    config.addinivalue_line("markers", "network: Tests requiring network access")
    config.addinivalue_line("markers", "ocr: Tests requiring OCR functionality")
    config.addinivalue_line("markers", "email: Tests requiring email functionality")
    config.addinivalue_line("markers", "file_system: Tests that modify file system")
    config.addinivalue_line("markers", "kindle: Tests requiring Kindle device")
    config.addinivalue_line("markers", "obsidian: Tests requiring Obsidian vault")


# Test collection hooks
def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on test names."""
    for item in items:
        # Add markers based on test file location
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "e2e" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)

        # Add markers based on test name
        if "slow" in item.name:
            item.add_marker(pytest.mark.slow)
        if "docker" in item.name:
            item.add_marker(pytest.mark.docker)
        if "network" in item.name:
            item.add_marker(pytest.mark.network)
        if "ocr" in item.name:
            item.add_marker(pytest.mark.ocr)
        if "email" in item.name:
            item.add_marker(pytest.mark.email)
        if "file_system" in item.name:
            item.add_marker(pytest.mark.file_system)
        if "kindle" in item.name:
            item.add_marker(pytest.mark.kindle)
        if "obsidian" in item.name:
            item.add_marker(pytest.mark.obsidian)
