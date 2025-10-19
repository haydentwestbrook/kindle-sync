"""Kindle Scribe synchronization functionality."""

import shutil
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Optional

import smtplib
from loguru import logger
from pathlib import Path

from .config import Config
from .core.exceptions import EmailServiceError, ErrorSeverity, FileProcessingError
from .core.retry import retry_on_file_error, retry_on_network_error
from .security.validation import FileValidationRequest, FileValidator


class KindleSync:
    """Handle synchronization with Kindle Scribe."""

    def __init__(self, config: Config):
        """Initialize Kindle sync."""
        self.config = config
        self.kindle_email = config.get_kindle_email()
        self.smtp_config = config.get_smtp_config()
        self.sync_config = config.get_sync_config()
        self.file_validator = FileValidator()

        logger.info("Kindle sync initialized")

    def send_pdf_to_kindle(self, pdf_path: Path, subject: Optional[str] = None) -> bool:
        """Send a PDF file to Kindle via email."""
        try:
            # Validate file before processing
            validation_request = FileValidationRequest(
                file_path=pdf_path,
                allowed_extensions=[".pdf"],
                allowed_mime_types=["application/pdf"],
            )
            validation_result = self.file_validator.validate_file(validation_request)

            if not validation_result.valid:
                raise FileProcessingError(
                    f"PDF validation failed: {validation_result.error}",
                    file_path=str(pdf_path),
                    severity=ErrorSeverity.HIGH,
                )

            # Generate subject if not provided
            if subject is None:
                subject = f"Document: {pdf_path.stem}"

            # Create email
            msg = MIMEMultipart()
            msg["From"] = self.smtp_config["username"]
            msg["To"] = self.kindle_email
            msg["Subject"] = subject

            # Add body text
            body = f"Please find attached: {pdf_path.name}"
            msg.attach(MIMEText(body, "plain"))

            # Attach PDF
            with open(pdf_path, "rb") as f:
                pdf_attachment = MIMEApplication(f.read(), _subtype="pdf")
                pdf_attachment.add_header(
                    "Content-Disposition", "attachment", filename=pdf_path.name
                )
                msg.attach(pdf_attachment)

            # Send email with retry
            self._send_email_with_retry(msg)

            logger.info(f"Sent {pdf_path.name} to Kindle")
            return True

        except FileProcessingError:
            raise
        except Exception as e:
            raise EmailServiceError(
                f"Error sending PDF to Kindle: {e}",
                email_address=self.kindle_email,
                severity=ErrorSeverity.HIGH,
            )

    @retry_on_network_error(max_attempts=3, wait_min=2.0, wait_max=30.0)
    def _send_email_with_retry(self, msg: MIMEMultipart):
        """Send email using SMTP with retry logic."""
        try:
            # Create SMTP session
            server = smtplib.SMTP(self.smtp_config["server"], self.smtp_config["port"])
            server.starttls()  # Enable TLS encryption
            server.login(self.smtp_config["username"], self.smtp_config["password"])

            # Send email
            text = msg.as_string()
            server.sendmail(self.smtp_config["username"], self.kindle_email, text)
            server.quit()

            logger.info("Email sent successfully")

        except Exception as e:
            raise EmailServiceError(
                f"Error sending email: {e}",
                email_address=self.kindle_email,
                severity=ErrorSeverity.HIGH,
            )

    def copy_to_kindle_usb(
        self, pdf_path: Path, kindle_path: Optional[Path] = None
    ) -> bool:
        """Copy PDF to Kindle via USB connection."""
        try:
            if not pdf_path.exists():
                logger.error(f"PDF file does not exist: {pdf_path}")
                return False

            # Default Kindle documents path
            if kindle_path is None:
                kindle_path = Path("/media/Kindle/documents")  # Linux
                if not kindle_path.exists():
                    kindle_path = Path("D:/documents")  # Windows
                if not kindle_path.exists():
                    kindle_path = Path("/Volumes/Kindle/documents")  # macOS

            if not kindle_path.exists():
                logger.error(f"Kindle documents folder not found: {kindle_path}")
                return False

            # Copy file
            destination = kindle_path / pdf_path.name
            shutil.copy2(pdf_path, destination)

            logger.info(f"Copied {pdf_path.name} to Kindle via USB")
            return True

        except Exception as e:
            logger.error(f"Error copying to Kindle USB: {e}")
            return False

    @retry_on_file_error(max_attempts=3, wait_min=0.5, wait_max=5.0)
    def backup_file(self, file_path: Path) -> Optional[Path]:
        """Create a backup of a file."""
        try:
            if not self.sync_config.get("backup_originals", True):
                return None

            # Validate file before backup
            validation_request = FileValidationRequest(
                file_path=file_path, max_size_mb=100  # Allow larger files for backup
            )
            validation_result = self.file_validator.validate_file(validation_request)

            if not validation_result.valid:
                raise FileProcessingError(
                    f"File validation failed for backup: {validation_result.error}",
                    file_path=str(file_path),
                    severity=ErrorSeverity.MEDIUM,
                )

            backup_folder = Path(self.sync_config.get("backup_folder", "Backups"))
            # Ensure backup_folder is a directory, not a file
            if backup_folder.exists() and not backup_folder.is_dir():
                backup_folder.unlink()  # Remove if it's a file
            backup_folder.mkdir(parents=True, exist_ok=True)

            # Create backup with timestamp
            from datetime import datetime

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{file_path.stem}_{timestamp}{file_path.suffix}"
            backup_path = backup_folder / backup_name

            shutil.copy2(file_path, backup_path)

            logger.info(f"Created backup: {backup_path}")
            return backup_path

        except FileProcessingError:
            raise
        except Exception as e:
            raise FileProcessingError(
                f"Error creating backup: {e}",
                file_path=str(file_path),
                severity=ErrorSeverity.MEDIUM,
            )

    def get_kindle_documents(self, kindle_path: Optional[Path] = None) -> List[Path]:
        """Get list of documents from Kindle."""
        try:
            if kindle_path is None:
                kindle_path = Path("/media/Kindle/documents")  # Linux
                if not kindle_path.exists():
                    kindle_path = Path("D:/documents")  # Windows
                if not kindle_path.exists():
                    kindle_path = Path("/Volumes/Kindle/documents")  # macOS

            if not kindle_path.exists():
                logger.warning(f"Kindle documents folder not found: {kindle_path}")
                return []

            # Get PDF files
            pdf_files = list(kindle_path.glob("*.pdf"))
            logger.info(f"Found {len(pdf_files)} PDF files on Kindle")

            return pdf_files

        except Exception as e:
            logger.error(f"Error getting Kindle documents: {e}")
            return []

    def sync_from_kindle(
        self, kindle_path: Optional[Path] = None, sync_folder: Optional[Path] = None
    ) -> List[Path]:
        """Sync documents from Kindle to sync folder."""
        try:
            if sync_folder is None:
                sync_folder = self.config.get_sync_folder_path()

            kindle_docs = self.get_kindle_documents(kindle_path)
            synced_files = []

            for doc_path in kindle_docs:
                # Check if file already exists in sync folder
                sync_file = sync_folder / doc_path.name
                if sync_file.exists():
                    logger.debug(f"File already exists in sync folder: {doc_path.name}")
                    continue

                # Copy file to sync folder
                shutil.copy2(doc_path, sync_file)
                synced_files.append(sync_file)

                logger.info(f"Synced {doc_path.name} from Kindle")

            return synced_files

        except Exception as e:
            logger.error(f"Error syncing from Kindle: {e}")
            return []

    def cleanup_old_files(self, folder: Path, max_age_days: int = 30) -> int:
        """Clean up old files from a folder."""
        try:
            import time

            cutoff_time = time.time() - (max_age_days * 24 * 60 * 60)
            cleaned_count = 0

            for file_path in folder.iterdir():
                if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                    file_path.unlink()
                    cleaned_count += 1
                    logger.info(f"Cleaned up old file: {file_path.name}")

            logger.info(f"Cleaned up {cleaned_count} old files")
            return cleaned_count

        except Exception as e:
            logger.error(f"Error cleaning up old files: {e}")
            return 0
