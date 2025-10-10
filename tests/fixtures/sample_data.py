"""Sample data fixtures for testing."""

from pathlib import Path
from typing import Dict, Any, List
import yaml


class SampleData:
    """Collection of sample data for testing."""
    
    # Sample markdown content
    SAMPLE_MARKDOWN = """# Kindle Scribe Sync Test Document

This is a comprehensive test document for the Kindle Scribe sync system.

## Features

The system provides the following features:

- **Automated file watching**: Monitors Obsidian vault for changes
- **PDF conversion**: Converts between Markdown and PDF formats
- **OCR processing**: Extracts text from handwritten notes
- **Email integration**: Sends documents to Kindle via email
- **Backup system**: Creates automatic backups of processed files

### Code Examples

Here's a Python code example:

```python
def sync_document(markdown_file: Path) -> Path:
    \"\"\"Convert markdown to PDF and send to Kindle.\"\"\"
    pdf_converter = MarkdownToPDFConverter(config)
    pdf_path = pdf_converter.convert_markdown_to_pdf(markdown_file)
    
    kindle_sync = KindleSync(config)
    kindle_sync.send_pdf_to_kindle(pdf_path)
    
    return pdf_path
```

### Lists and Tables

#### Task List
- [x] Set up file watcher
- [x] Implement PDF conversion
- [ ] Add OCR processing
- [ ] Test email integration

#### Data Table
| Component | Status | Priority |
|-----------|--------|----------|
| File Watcher | Complete | High |
| PDF Converter | Complete | High |
| OCR Processor | In Progress | Medium |
| Email Integration | Pending | Medium |

### Mathematical Content

The system processes documents with the following formula:

$$E = mc^2$$

Where:
- E = Energy
- m = Mass  
- c = Speed of light

### Special Characters

The system handles various special characters:
- Quotes: "double" and 'single'
- Symbols: @#$%^&*()
- Currency: €£¥$
- Math: α + β = γ

### Unicode Content

- English: Hello, World!
- Chinese: 你好，世界！
- Japanese: こんにちは、世界！
- Arabic: مرحبا بالعالم!
- Emoji: 🚀📚💻

## Conclusion

This document tests the complete functionality of the Kindle Scribe sync system.
"""

    # Sample PDF content (minimal valid PDF)
    SAMPLE_PDF_CONTENT = b"""%PDF-1.4
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

    # Sample configuration data
    SAMPLE_CONFIG = {
        "obsidian": {
            "vault_path": "/tmp/test_obsidian",
            "sync_folder": "Kindle Sync",
            "templates_folder": "Templates",
            "watch_subfolders": True
        },
        "kindle": {
            "email": "test@kindle.com",
            "approved_senders": ["test@example.com", "test2@example.com"],
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
            "smtp_username": "test@gmail.com",
            "smtp_password": "test_app_password"
        },
        "processing": {
            "ocr": {
                "language": "eng",
                "confidence_threshold": 60
            },
            "pdf": {
                "page_size": "A4",
                "margins": [72, 72, 72, 72],
                "font_family": "Times-Roman",
                "font_size": 12,
                "line_spacing": 1.2
            },
            "markdown": {
                "extensions": ["tables", "fenced_code", "toc", "footnotes"],
                "preserve_links": True
            }
        },
        "sync": {
            "auto_convert_on_save": True,
            "auto_send_to_kindle": True,
            "backup_originals": True,
            "backup_folder": "Backups"
        },
        "patterns": {
            "markdown_files": "*.md",
            "pdf_files": "*.pdf",
            "image_files": "*.{png,jpg,jpeg}"
        },
        "logging": {
            "level": "INFO",
            "file": "kindle_sync.log",
            "max_size": "10MB",
            "backup_count": 5
        },
        "advanced": {
            "debounce_time": 2.0,
            "max_file_size": "50MB",
            "concurrent_processing": True,
            "retry_attempts": 3
        }
    }

    # Sample OCR results
    SAMPLE_OCR_RESULTS = [
        {
            "text": "TITLE IN CAPS\nThis is a regular paragraph with some text.\n\nSHORT HEADING\nAnother paragraph with more content.",
            "confidence": 85.5,
            "language": "eng"
        },
        {
            "text": "Meeting Notes\n\nDate: 2024-01-15\nAttendees: John, Jane, Bob\n\nAgenda:\n1. Project status\n2. Budget review\n3. Next steps",
            "confidence": 92.3,
            "language": "eng"
        },
        {
            "text": "Handwritten Notes\n\n• Important point 1\n• Important point 2\n• Action item: Follow up\n\nQuestions:\n- What is the timeline?\n- Who is responsible?",
            "confidence": 78.1,
            "language": "eng"
        }
    ]

    # Sample email data
    SAMPLE_EMAIL_DATA = {
        "from": "test@gmail.com",
        "to": "test@kindle.com",
        "subject": "Document: Test Document",
        "body": "Please find attached: test_document.pdf",
        "attachment": "test_document.pdf"
    }

    # Sample file system events
    SAMPLE_FILE_EVENTS = [
        {
            "type": "created",
            "path": "/tmp/test_document.md",
            "is_directory": False
        },
        {
            "type": "modified",
            "path": "/tmp/test_document.md",
            "is_directory": False
        },
        {
            "type": "moved",
            "path": "/tmp/test_document_moved.md",
            "is_directory": False
        }
    ]

    # Sample processing statistics
    SAMPLE_STATISTICS = {
        "files_processed": 25,
        "pdfs_generated": 20,
        "pdfs_sent_to_kindle": 18,
        "markdown_files_created": 5,
        "errors": 2
    }

    # Sample error messages
    SAMPLE_ERRORS = [
        "Configuration validation failed: Obsidian vault path does not exist",
        "Error converting test.pdf to Markdown: OCR processing failed",
        "Error sending PDF to Kindle: SMTP connection timeout",
        "File too large to process: large_document.pdf (75MB)",
        "Permission denied: Cannot write to backup folder"
    ]

    # Sample file paths
    SAMPLE_FILE_PATHS = {
        "markdown": [
            "/tmp/test_document.md",
            "/tmp/meeting_notes.md",
            "/tmp/project_plan.md",
            "/tmp/ideas.md"
        ],
        "pdf": [
            "/tmp/test_document.pdf",
            "/tmp/meeting_notes.pdf",
            "/tmp/project_plan.pdf",
            "/tmp/ideas.pdf"
        ],
        "images": [
            "/tmp/diagram.png",
            "/tmp/screenshot.jpg",
            "/tmp/photo.jpeg"
        ]
    }

    # Sample directory structures
    SAMPLE_DIRECTORY_STRUCTURE = {
        "obsidian_vault": {
            "Kindle Sync": {
                "Drafts": {},
                "Final": {},
                "Archive": {}
            },
            "Templates": {
                "meeting_template.md": "content",
                "project_template.md": "content"
            },
            "Backups": {
                "2024-01-15": {},
                "2024-01-14": {}
            }
        }
    }

    @classmethod
    def get_sample_config(cls, **overrides) -> Dict[str, Any]:
        """Get sample configuration with optional overrides."""
        config = cls.SAMPLE_CONFIG.copy()
        
        # Deep merge overrides
        for key, value in overrides.items():
            if isinstance(value, dict) and key in config and isinstance(config[key], dict):
                config[key].update(value)
            else:
                config[key] = value
        
        return config

    @classmethod
    def create_sample_files(cls, base_path: Path) -> Dict[str, Path]:
        """Create sample files in the given directory."""
        files = {}
        
        # Create markdown file
        md_file = base_path / "sample_document.md"
        md_file.write_text(cls.SAMPLE_MARKDOWN)
        files["markdown"] = md_file
        
        # Create PDF file
        pdf_file = base_path / "sample_document.pdf"
        pdf_file.write_bytes(cls.SAMPLE_PDF_CONTENT)
        files["pdf"] = pdf_file
        
        # Create config file
        config_file = base_path / "sample_config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(cls.SAMPLE_CONFIG, f)
        files["config"] = config_file
        
        return files

    @classmethod
    def create_sample_directory_structure(cls, base_path: Path) -> Dict[str, Path]:
        """Create sample directory structure."""
        paths = {}
        
        def create_structure(structure: Dict, current_path: Path):
            for name, content in structure.items():
                item_path = current_path / name
                if isinstance(content, dict):
                    item_path.mkdir(exist_ok=True)
                    paths[name] = item_path
                    create_structure(content, item_path)
                else:
                    item_path.write_text(content)
                    paths[name] = item_path
        
        create_structure(cls.SAMPLE_DIRECTORY_STRUCTURE, base_path)
        return paths

    @classmethod
    def get_sample_ocr_result(cls, index: int = 0) -> Dict[str, Any]:
        """Get a sample OCR result by index."""
        return cls.SAMPLE_OCR_RESULTS[index % len(cls.SAMPLE_OCR_RESULTS)]

    @classmethod
    def get_sample_file_path(cls, file_type: str, index: int = 0) -> str:
        """Get a sample file path by type and index."""
        return cls.SAMPLE_FILE_PATHS[file_type][index % len(cls.SAMPLE_FILE_PATHS[file_type])]

    @classmethod
    def get_sample_error(cls, index: int = 0) -> str:
        """Get a sample error message by index."""
        return cls.SAMPLE_ERRORS[index % len(cls.SAMPLE_ERRORS)]

    @classmethod
    def get_sample_statistics(cls, **overrides) -> Dict[str, Any]:
        """Get sample statistics with optional overrides."""
        stats = cls.SAMPLE_STATISTICS.copy()
        stats.update(overrides)
        return stats
