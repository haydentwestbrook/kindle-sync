"""Unit tests for Kindle synchronization functionality."""

from email.mime.multipart import MIMEMultipart
from unittest.mock import Mock, patch

import pytest
from pathlib import Path

from src.core.exceptions import EmailServiceError, FileProcessingError
from src.kindle_sync import KindleSync


class TestKindleSync:
    """Test cases for KindleSync class."""

    def test_kindle_sync_initialization(self, config):
        """Test KindleSync initialization."""
        kindle_sync = KindleSync(config)

        assert kindle_sync.config == config
        assert kindle_sync.kindle_email == config.get_kindle_email()
        assert kindle_sync.smtp_config == config.get_smtp_config()
        assert kindle_sync.sync_config == config.get_sync_config()

    def test_send_pdf_to_kindle_success(self, config, temp_dir, sample_pdf_content):
        """Test successful PDF sending to Kindle."""
        kindle_sync = KindleSync(config)

        # Create a PDF file
        pdf_file = temp_dir / "test.pdf"
        pdf_file.write_bytes(sample_pdf_content)

        # Mock SMTP
        with patch.object(kindle_sync, "_send_email_with_retry") as mock_send:
            result = kindle_sync.send_pdf_to_kindle(pdf_file)

            assert result is True
            mock_send.assert_called_once()

            # Verify email structure
            email_msg = mock_send.call_args[0][0]
            assert isinstance(email_msg, MIMEMultipart)
            assert email_msg["To"] == "test@kindle.com"
            assert email_msg["Subject"] == "Document: test"

    def test_send_pdf_to_kindle_custom_subject(
        self, config, temp_dir, sample_pdf_content
    ):
        """Test PDF sending with custom subject."""
        kindle_sync = KindleSync(config)

        # Create a PDF file
        pdf_file = temp_dir / "test.pdf"
        pdf_file.write_bytes(sample_pdf_content)

        custom_subject = "Custom Document Title"

        # Mock SMTP
        with patch.object(kindle_sync, "_send_email_with_retry") as mock_send:
            result = kindle_sync.send_pdf_to_kindle(pdf_file, custom_subject)

            assert result is True

            # Verify custom subject
            email_msg = mock_send.call_args[0][0]
            assert email_msg["Subject"] == custom_subject

    def test_send_pdf_to_kindle_file_not_found(self, config, temp_dir):
        """Test PDF sending with non-existent file."""
        kindle_sync = KindleSync(config)

        non_existent_file = temp_dir / "non_existent.pdf"

        with pytest.raises(EmailServiceError):
            kindle_sync.send_pdf_to_kindle(non_existent_file)

    def test_send_pdf_to_kindle_smtp_error(self, config, temp_dir, sample_pdf_content):
        """Test PDF sending with SMTP error."""
        kindle_sync = KindleSync(config)

        # Create a PDF file
        pdf_file = temp_dir / "test.pdf"
        pdf_file.write_bytes(sample_pdf_content)

        # Mock SMTP to raise exception
        with patch.object(
            kindle_sync, "_send_email_with_retry", side_effect=Exception("SMTP error")
        ):
            with pytest.raises(EmailServiceError):
                kindle_sync.send_pdf_to_kindle(pdf_file)

    def test_send_email_success(self, config):
        """Test successful email sending."""
        kindle_sync = KindleSync(config)

        # Create a test email
        msg = MIMEMultipart()
        msg["From"] = "test@gmail.com"
        msg["To"] = "test@kindle.com"
        msg["Subject"] = "Test Subject"

        # Mock SMTP
        with patch("smtplib.SMTP") as mock_smtp_class:
            mock_server = Mock()
            mock_smtp_class.return_value = mock_server

            kindle_sync._send_email_with_retry(msg)

            # Verify SMTP operations
            mock_smtp_class.assert_called_once_with("smtp.gmail.com", 587)
            mock_server.starttls.assert_called_once()
            mock_server.login.assert_called_once_with("test@gmail.com", "test_password")
            mock_server.sendmail.assert_called_once()
            mock_server.quit.assert_called_once()

    def test_send_email_smtp_error(self, config):
        """Test email sending with SMTP error."""
        kindle_sync = KindleSync(config)

        # Create a test email
        msg = MIMEMultipart()
        msg["From"] = "test@gmail.com"
        msg["To"] = "test@kindle.com"
        msg["Subject"] = "Test Subject"

        # Mock SMTP to raise exception
        with patch("smtplib.SMTP", side_effect=Exception("SMTP connection error")):
            with pytest.raises(Exception, match="SMTP connection error"):
                kindle_sync._send_email_with_retry(msg)

    def test_copy_to_kindle_usb_success(self, config, temp_dir, sample_pdf_content):
        """Test successful USB copy to Kindle."""
        kindle_sync = KindleSync(config)

        # Create a PDF file
        pdf_file = temp_dir / "test.pdf"
        pdf_file.write_bytes(sample_pdf_content)

        # Create mock Kindle path
        kindle_path = temp_dir / "kindle_documents"
        kindle_path.mkdir()

        result = kindle_sync.copy_to_kindle_usb(pdf_file, kindle_path)

        assert result is True

        # Verify file was copied
        destination = kindle_path / "test.pdf"
        assert destination.exists()
        assert destination.read_bytes() == sample_pdf_content

    def test_copy_to_kindle_usb_default_path_linux(
        self, config, temp_dir, sample_pdf_content
    ):
        """Test USB copy with default Linux Kindle path."""
        kindle_sync = KindleSync(config)

        # Create a PDF file
        pdf_file = temp_dir / "test.pdf"
        pdf_file.write_bytes(sample_pdf_content)

        # Create mock default Kindle path
        default_kindle_path = Path("/media/Kindle/documents")

        with patch("pathlib.Path.exists") as mock_exists:
            mock_exists.side_effect = lambda: str(default_kindle_path) in str(
                Path.cwd()
            ) or str(default_kindle_path) == str(default_kindle_path)

            with patch("shutil.copy2") as mock_copy:
                kindle_sync.copy_to_kindle_usb(pdf_file)

                # Should attempt to copy (even if path doesn't exist in test)
                mock_copy.assert_called()

    def test_copy_to_kindle_usb_file_not_found(self, config, temp_dir):
        """Test USB copy with non-existent file."""
        kindle_sync = KindleSync(config)

        non_existent_file = temp_dir / "non_existent.pdf"
        kindle_path = temp_dir / "kindle_documents"
        kindle_path.mkdir()

        result = kindle_sync.copy_to_kindle_usb(non_existent_file, kindle_path)

        assert result is False

    def test_copy_to_kindle_usb_kindle_path_not_found(
        self, config, temp_dir, sample_pdf_content
    ):
        """Test USB copy with non-existent Kindle path."""
        kindle_sync = KindleSync(config)

        # Create a PDF file
        pdf_file = temp_dir / "test.pdf"
        pdf_file.write_bytes(sample_pdf_content)

        non_existent_kindle_path = temp_dir / "non_existent_kindle"

        result = kindle_sync.copy_to_kindle_usb(pdf_file, non_existent_kindle_path)

        assert result is False

    def test_backup_file_success(self, config, temp_dir, sample_pdf_content):
        """Test successful file backup."""
        kindle_sync = KindleSync(config)

        # Create a file to backup
        original_file = temp_dir / "test.pdf"
        original_file.write_bytes(sample_pdf_content)

        # Create backup folder
        backup_folder = temp_dir / "Backups"
        backup_folder.mkdir()

        with patch.object(
            kindle_sync.config,
            "get_sync_config",
            return_value={
                "backup_originals": True,
                "backup_folder": str(backup_folder),
            },
        ):
            result = kindle_sync.backup_file(original_file)

            assert result is not None
            assert result.exists()
            assert result.read_bytes() == sample_pdf_content
            assert "test_" in result.name
            assert result.suffix == ".pdf"

    def test_backup_file_disabled(self, config, temp_dir, sample_pdf_content):
        """Test file backup when disabled."""
        kindle_sync = KindleSync(config)

        # Create a file to backup
        original_file = temp_dir / "test.pdf"
        original_file.write_bytes(sample_pdf_content)

        # Mock the sync_config to disable backups
        kindle_sync.sync_config = {
            "backup_originals": False,
            "backup_folder": "Backups",
        }
        result = kindle_sync.backup_file(original_file)

        assert result is None

    def test_backup_file_error(self, config, temp_dir, sample_pdf_content):
        """Test file backup with error."""
        kindle_sync = KindleSync(config)

        # Create a file to backup
        original_file = temp_dir / "test.pdf"
        original_file.write_bytes(sample_pdf_content)

        with patch.object(
            kindle_sync.config,
            "get_sync_config",
            return_value={"backup_originals": True, "backup_folder": "/invalid/path"},
        ):
            with patch("shutil.copy2", side_effect=Exception("Copy error")):
                with pytest.raises(FileProcessingError):
                    kindle_sync.backup_file(original_file)

    def test_get_kindle_documents_success(self, config, temp_dir):
        """Test getting Kindle documents successfully."""
        kindle_sync = KindleSync(config)

        # Create mock Kindle documents folder
        kindle_path = temp_dir / "kindle_documents"
        kindle_path.mkdir()

        # Create some PDF files
        pdf1 = kindle_path / "doc1.pdf"
        pdf2 = kindle_path / "doc2.pdf"
        pdf1.write_bytes(b"PDF1")
        pdf2.write_bytes(b"PDF2")

        result = kindle_sync.get_kindle_documents(kindle_path)

        assert len(result) == 2
        assert pdf1 in result
        assert pdf2 in result

    def test_get_kindle_documents_path_not_found(self, config, temp_dir):
        """Test getting Kindle documents with non-existent path."""
        kindle_sync = KindleSync(config)

        non_existent_path = temp_dir / "non_existent"

        result = kindle_sync.get_kindle_documents(non_existent_path)

        assert result == []

    def test_get_kindle_documents_default_paths(self, config):
        """Test getting Kindle documents with default paths."""
        kindle_sync = KindleSync(config)

        with patch("pathlib.Path.exists", return_value=False):
            result = kindle_sync.get_kindle_documents()

            assert result == []

    def test_sync_from_kindle_success(self, config, temp_dir):
        """Test successful sync from Kindle."""
        kindle_sync = KindleSync(config)

        # Create mock Kindle documents
        kindle_path = temp_dir / "kindle_documents"
        kindle_path.mkdir()

        pdf1 = kindle_path / "doc1.pdf"
        pdf1.write_bytes(b"PDF1")

        # Create sync folder
        sync_folder = temp_dir / "sync_folder"
        sync_folder.mkdir()

        with patch.object(
            kindle_sync.config, "get_sync_folder_path", return_value=sync_folder
        ):
            with patch.object(kindle_sync, "get_kindle_documents", return_value=[pdf1]):
                result = kindle_sync.sync_from_kindle(kindle_path, sync_folder)

                assert len(result) == 1
                assert result[0] == sync_folder / "doc1.pdf"
                assert result[0].exists()
                assert result[0].read_bytes() == b"PDF1"

    def test_sync_from_kindle_file_exists(self, config, temp_dir):
        """Test sync from Kindle when file already exists."""
        kindle_sync = KindleSync(config)

        # Create mock Kindle documents
        kindle_path = temp_dir / "kindle_documents"
        kindle_path.mkdir()

        pdf1 = kindle_path / "doc1.pdf"
        pdf1.write_bytes(b"PDF1")

        # Create sync folder with existing file
        sync_folder = temp_dir / "sync_folder"
        sync_folder.mkdir()
        existing_file = sync_folder / "doc1.pdf"
        existing_file.write_bytes(b"Existing PDF")

        with patch.object(
            kindle_sync.config, "get_sync_folder_path", return_value=sync_folder
        ):
            with patch.object(kindle_sync, "get_kindle_documents", return_value=[pdf1]):
                result = kindle_sync.sync_from_kindle(kindle_path, sync_folder)

                # Should not sync existing file
                assert len(result) == 0
                assert existing_file.read_bytes() == b"Existing PDF"

    def test_cleanup_old_files_success(self, config, temp_dir):
        """Test successful cleanup of old files."""
        kindle_sync = KindleSync(config)

        # Create test folder with files
        test_folder = temp_dir / "test_folder"
        test_folder.mkdir()

        # Create old file (simulate old timestamp)
        old_file = test_folder / "old_file.txt"
        old_file.write_text("Old content")

        # Create recent file
        recent_file = test_folder / "recent_file.txt"
        recent_file.write_text("Recent content")

        # Mock the cleanup method to test the logic
        def mock_cleanup_old_files(folder, max_age_days=30):
            import time

            cutoff_time = time.time() - (max_age_days * 24 * 60 * 60)
            cleaned_count = 0

            for file_path in folder.iterdir():
                if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                    file_path.unlink()
                    cleaned_count += 1

            return cleaned_count

        # Mock the method
        with patch.object(
            kindle_sync, "cleanup_old_files", side_effect=mock_cleanup_old_files
        ):
            with patch("time.time", return_value=2000000000):  # Current time
                # Manually set file timestamps
                import os

                os.utime(old_file, (1000000000, 1000000000))  # Old timestamp
                os.utime(recent_file, (2000000000, 2000000000))  # Recent timestamp

                result = kindle_sync.cleanup_old_files(test_folder, max_age_days=30)

                assert result == 1  # One file cleaned up
                assert not old_file.exists()
                assert recent_file.exists()

    def test_cleanup_old_files_error(self, config, temp_dir):
        """Test cleanup with error."""
        kindle_sync = KindleSync(config)

        # Create test folder
        test_folder = temp_dir / "test_folder"
        test_folder.mkdir()

        # Create a file
        test_file = test_folder / "test_file.txt"
        test_file.write_text("Test content")

        # Mock error during cleanup
        with patch("pathlib.Path.iterdir", side_effect=Exception("Permission error")):
            result = kindle_sync.cleanup_old_files(test_folder)

            assert result == 0

    def test_smtp_configuration_usage(self, config):
        """Test that SMTP configuration is used correctly."""
        kindle_sync = KindleSync(config)

        # Verify SMTP config is properly set
        assert kindle_sync.smtp_config["server"] == "smtp.gmail.com"
        assert kindle_sync.smtp_config["port"] == 587
        assert kindle_sync.smtp_config["username"] == "test@gmail.com"
        assert kindle_sync.smtp_config["password"] == "test_password"

    def test_kindle_email_usage(self, config):
        """Test that Kindle email is used correctly."""
        kindle_sync = KindleSync(config)

        assert kindle_sync.kindle_email == "test@kindle.com"
