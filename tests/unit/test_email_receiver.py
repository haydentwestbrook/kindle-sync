"""
Unit tests for email receiver functionality.

Tests the email receiving and processing functionality.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

from src.email_receiver import EmailReceiver
from src.config import Config
from src.core.exceptions import EmailServiceError, ErrorSeverity


class TestEmailReceiver:
    """Test cases for EmailReceiver."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration."""
        config = Mock(spec=Config)
        config.get.side_effect = lambda key, default=None: {
            "email_receiving.enabled": True,
            "email_receiving.imap_server": "imap.gmail.com",
            "email_receiving.imap_port": 993,
            "email_receiving.username": "test@example.com",
            "email_receiving.password": "test_password",
            "email_receiving.check_interval": 300,
            "email_receiving.max_emails_per_check": 10,
            "email_receiving.mark_as_read": True,
            "email_receiving.delete_after_processing": False,
            "email_receiving.prevent_duplicates": True,
            "email_receiving.duplicate_tracking_file": "/tmp/processed_emails.txt"
        }.get(key, default)
        
        # Mock config methods
        config.get_kindle_email.return_value = "kindle@example.com"
        config.get_approved_senders.return_value = ["test@example.com", "kindle@example.com"]
        return config

    @pytest.fixture
    def email_receiver(self, mock_config):
        """Create an EmailReceiver instance."""
        return EmailReceiver(mock_config)

    @pytest.fixture
    def temp_directory(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    def test_email_receiver_initialization(self, mock_config):
        """Test email receiver initialization."""
        receiver = EmailReceiver(mock_config)
        assert receiver.config == mock_config
        assert receiver.imap_config is not None
        assert receiver.kindle_email == "kindle@example.com"
        assert receiver.approved_senders == ["test@example.com", "kindle@example.com"]

    def test_email_receiver_disabled(self, mock_config):
        """Test email receiver when disabled."""
        mock_config.get.side_effect = lambda key, default=None: {
            "email_receiving.enabled": False
        }.get(key, default)
        
        receiver = EmailReceiver(mock_config)
        assert receiver.enabled is False

    @patch('src.email_receiver.imaplib.IMAP4_SSL')
    def test_connect_to_imap_success(self, mock_imap, email_receiver):
        """Test successful IMAP connection."""
        # Mock IMAP connection
        mock_imap_instance = Mock()
        mock_imap.return_value = mock_imap_instance
        mock_imap_instance.login.return_value = ("OK", [b"Login successful"])
        
        result = email_receiver._connect_to_imap()
        
        assert result == mock_imap_instance
        mock_imap.assert_called_once_with("imap.gmail.com", 993)
        mock_imap_instance.login.assert_called_once_with("test@example.com", "test_password")

    @patch('src.email_receiver.imaplib.IMAP4_SSL')
    def test_connect_to_imap_connection_error(self, mock_imap, email_receiver):
        """Test IMAP connection error."""
        # Mock connection error
        mock_imap.side_effect = Exception("Connection failed")
        
        with pytest.raises(EmailServiceError) as exc_info:
            email_receiver._connect_to_imap()
        
        assert exc_info.value.severity == ErrorSeverity.HIGH
        assert "Failed to connect to IMAP server" in str(exc_info.value)

    @patch('src.email_receiver.imaplib.IMAP4_SSL')
    def test_connect_to_imap_login_error(self, mock_imap, email_receiver):
        """Test IMAP login error."""
        # Mock IMAP connection
        mock_imap_instance = Mock()
        mock_imap.return_value = mock_imap_instance
        mock_imap_instance.login.return_value = ("NO", [b"Login failed"])
        
        with pytest.raises(EmailServiceError) as exc_info:
            email_receiver._connect_to_imap()
        
        assert exc_info.value.severity == ErrorSeverity.HIGH
        assert "Failed to login to IMAP server" in str(exc_info.value)

    def test_is_approved_sender_approved(self, email_receiver):
        """Test checking approved sender."""
        assert email_receiver._is_approved_sender("test@example.com") is True
        assert email_receiver._is_approved_sender("kindle@example.com") is True

    def test_is_approved_sender_not_approved(self, email_receiver):
        """Test checking non-approved sender."""
        assert email_receiver._is_approved_sender("spam@example.com") is False
        assert email_receiver._is_approved_sender("unknown@example.com") is False

    def test_is_approved_sender_case_insensitive(self, email_receiver):
        """Test approved sender check is case insensitive."""
        assert email_receiver._is_approved_sender("TEST@EXAMPLE.COM") is True
        assert email_receiver._is_approved_sender("Test@Example.Com") is True

    def test_extract_pdf_attachments_success(self, email_receiver):
        """Test successful PDF attachment extraction."""
        # Create a mock email with PDF attachment
        msg = MIMEMultipart()
        msg['From'] = "test@example.com"
        msg['To'] = "kindle@example.com"
        msg['Subject'] = "Test PDF"
        
        # Add PDF attachment
        pdf_attachment = MIMEApplication(b"PDF content", _subtype="pdf")
        pdf_attachment.add_header('Content-Disposition', 'attachment', filename='test.pdf')
        msg.attach(pdf_attachment)
        
        attachments = email_receiver._extract_pdf_attachments(msg)
        
        assert len(attachments) == 1
        assert attachments[0]['filename'] == 'test.pdf'
        assert attachments[0]['content'] == b"PDF content"

    def test_extract_pdf_attachments_no_pdf(self, email_receiver):
        """Test email with no PDF attachments."""
        # Create a mock email without PDF attachment
        msg = MIMEMultipart()
        msg['From'] = "test@example.com"
        msg['To'] = "kindle@example.com"
        msg['Subject'] = "Test Email"
        
        # Add text attachment
        text_attachment = MIMEText("Text content", _subtype="plain")
        text_attachment.add_header('Content-Disposition', 'attachment', filename='test.txt')
        msg.attach(text_attachment)
        
        attachments = email_receiver._extract_pdf_attachments(msg)
        
        assert len(attachments) == 0

    def test_extract_pdf_attachments_multiple_pdfs(self, email_receiver):
        """Test email with multiple PDF attachments."""
        # Create a mock email with multiple PDF attachments
        msg = MIMEMultipart()
        msg['From'] = "test@example.com"
        msg['To'] = "kindle@example.com"
        msg['Subject'] = "Multiple PDFs"
        
        # Add first PDF
        pdf1 = MIMEApplication(b"PDF 1 content", _subtype="pdf")
        pdf1.add_header('Content-Disposition', 'attachment', filename='test1.pdf')
        msg.attach(pdf1)
        
        # Add second PDF
        pdf2 = MIMEApplication(b"PDF 2 content", _subtype="pdf")
        pdf2.add_header('Content-Disposition', 'attachment', filename='test2.pdf')
        msg.attach(pdf2)
        
        attachments = email_receiver._extract_pdf_attachments(msg)
        
        assert len(attachments) == 2
        assert attachments[0]['filename'] == 'test1.pdf'
        assert attachments[1]['filename'] == 'test2.pdf'

    def test_save_pdf_attachment_success(self, email_receiver, temp_directory):
        """Test successful PDF attachment saving."""
        # Mock the sync folder path
        email_receiver.config.get_sync_folder_path.return_value = temp_directory
        
        attachment = {
            'filename': 'test.pdf',
            'content': b"PDF content"
        }
        
        result = email_receiver._save_pdf_attachment(attachment)
        
        assert result is not None
        assert result.exists()
        assert result.name == 'test.pdf'
        assert result.read_bytes() == b"PDF content"

    def test_save_pdf_attachment_duplicate_filename(self, email_receiver, temp_directory):
        """Test saving PDF attachment with duplicate filename."""
        # Mock the sync folder path
        email_receiver.config.get_sync_folder_path.return_value = temp_directory
        
        # Create existing file
        existing_file = temp_directory / "test.pdf"
        existing_file.write_bytes(b"Existing content")
        
        attachment = {
            'filename': 'test.pdf',
            'content': b"New PDF content"
        }
        
        result = email_receiver._save_pdf_attachment(attachment)
        
        assert result is not None
        assert result.exists()
        # Should have a different name due to duplicate
        assert result.name != "test.pdf" or result.read_bytes() == b"New PDF content"

    def test_save_pdf_attachment_error(self, email_receiver):
        """Test PDF attachment saving error."""
        # Mock invalid sync folder path
        email_receiver.config.get_sync_folder_path.return_value = Path("/invalid/path")
        
        attachment = {
            'filename': 'test.pdf',
            'content': b"PDF content"
        }
        
        with pytest.raises(EmailServiceError) as exc_info:
            email_receiver._save_pdf_attachment(attachment)
        
        assert exc_info.value.severity == ErrorSeverity.MEDIUM
        assert "Failed to save PDF attachment" in str(exc_info.value)

    def test_mark_email_as_read_success(self, email_receiver):
        """Test successful email marking as read."""
        mock_imap = Mock()
        mock_imap.store.return_value = ("OK", [b"Email marked as read"])
        
        result = email_receiver._mark_email_as_read(mock_imap, "123")
        
        assert result is True
        mock_imap.store.assert_called_once_with("123", "+FLAGS", "\\Seen")

    def test_mark_email_as_read_error(self, email_receiver):
        """Test email marking as read error."""
        mock_imap = Mock()
        mock_imap.store.return_value = ("NO", [b"Failed to mark as read"])
        
        result = email_receiver._mark_email_as_read(mock_imap, "123")
        
        assert result is False

    def test_delete_email_success(self, email_receiver):
        """Test successful email deletion."""
        mock_imap = Mock()
        mock_imap.store.return_value = ("OK", [b"Email marked for deletion"])
        mock_imap.expunge.return_value = ("OK", [b"Email deleted"])
        
        result = email_receiver._delete_email(mock_imap, "123")
        
        assert result is True
        mock_imap.store.assert_called_once_with("123", "+FLAGS", "\\Deleted")
        mock_imap.expunge.assert_called_once()

    def test_delete_email_error(self, email_receiver):
        """Test email deletion error."""
        mock_imap = Mock()
        mock_imap.store.return_value = ("NO", [b"Failed to delete"])
        
        result = email_receiver._delete_email(mock_imap, "123")
        
        assert result is False

    def test_is_duplicate_email_not_duplicate(self, email_receiver, temp_directory):
        """Test checking non-duplicate email."""
        # Mock tracking file path
        tracking_file = temp_directory / "processed_emails.txt"
        email_receiver.config.get.side_effect = lambda key, default=None: {
            "email_receiving.duplicate_tracking_file": str(tracking_file)
        }.get(key, default)
        
        # Create tracking file with different email ID
        tracking_file.write_text("different_email_id\n")
        
        result = email_receiver._is_duplicate_email("new_email_id")
        
        assert result is False

    def test_is_duplicate_email_duplicate(self, email_receiver, temp_directory):
        """Test checking duplicate email."""
        # Mock tracking file path
        tracking_file = temp_directory / "processed_emails.txt"
        email_receiver.config.get.side_effect = lambda key, default=None: {
            "email_receiving.duplicate_tracking_file": str(tracking_file)
        }.get(key, default)
        
        # Create tracking file with same email ID
        tracking_file.write_text("test_email_id\n")
        
        result = email_receiver._is_duplicate_email("test_email_id")
        
        assert result is True

    def test_record_processed_email(self, email_receiver, temp_directory):
        """Test recording processed email."""
        # Mock tracking file path
        tracking_file = temp_directory / "processed_emails.txt"
        email_receiver.config.get.side_effect = lambda key, default=None: {
            "email_receiving.duplicate_tracking_file": str(tracking_file)
        }.get(key, default)
        
        email_receiver._record_processed_email("test_email_id")
        
        assert tracking_file.exists()
        content = tracking_file.read_text()
        assert "test_email_id" in content

    def test_get_statistics(self, email_receiver):
        """Test getting email receiver statistics."""
        stats = email_receiver.get_statistics()
        
        assert "emails_checked" in stats
        assert "emails_processed" in stats
        assert "pdfs_extracted" in stats
        assert "errors" in stats

    def test_reset_statistics(self, email_receiver):
        """Test resetting email receiver statistics."""
        # Set some statistics
        email_receiver.stats["emails_checked"] = 10
        email_receiver.stats["emails_processed"] = 5
        
        email_receiver.reset_statistics()
        
        assert email_receiver.stats["emails_checked"] == 0
        assert email_receiver.stats["emails_processed"] == 0
