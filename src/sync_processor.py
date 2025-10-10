"""Main sync processor that coordinates all components."""

from pathlib import Path
from typing import Any, Dict, Optional

from loguru import logger

from .config import Config
from .file_watcher import ObsidianFileWatcher
from .kindle_sync import KindleSync
from .pdf_converter import MarkdownToPDFConverter, PDFToMarkdownConverter


class SyncProcessor:
    """Main processor that coordinates the sync workflow."""

    def __init__(self, config: Config):
        """Initialize the sync processor."""
        self.config = config
        self.file_watcher = ObsidianFileWatcher(config, self._process_file)
        self.markdown_to_pdf = MarkdownToPDFConverter(config)
        self.pdf_to_markdown = PDFToMarkdownConverter(config)
        self.kindle_sync = KindleSync(config)

        # Statistics
        self.stats = {
            "files_processed": 0,
            "pdfs_generated": 0,
            "pdfs_sent_to_kindle": 0,
            "markdown_files_created": 0,
            "errors": 0,
        }

        logger.info("Sync processor initialized")

    def start(self):
        """Start the sync system."""
        try:
            # Validate configuration
            if not self.config.validate():
                logger.error("Configuration validation failed")
                return False

            # Start file watcher
            self.file_watcher.start()

            logger.info("Sync system started successfully")
            return True

        except Exception as e:
            logger.error(f"Error starting sync system: {e}")
            return False

    def stop(self):
        """Stop the sync system."""
        try:
            self.file_watcher.stop()
            logger.info("Sync system stopped")
        except Exception as e:
            logger.error(f"Error stopping sync system: {e}")

    def _process_file(self, file_path: Path):
        """Process a file change event."""
        try:
            logger.info(f"Processing file: {file_path}")

            # Determine file type and processing method
            if file_path.suffix.lower() == ".md":
                self._process_markdown_file(file_path)
            elif file_path.suffix.lower() == ".pdf":
                self._process_pdf_file(file_path)
            else:
                logger.debug(f"Unsupported file type: {file_path.suffix}")
                return

            self.stats["files_processed"] += 1

        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")
            self.stats["errors"] += 1

    def _process_markdown_file(self, markdown_path: Path):
        """Process a Markdown file."""
        try:
            # Check if auto-convert is enabled
            if not self.config.get("sync.auto_convert_on_save", True):
                logger.debug("Auto-convert disabled, skipping PDF generation")
                return

            # Create backup
            self.kindle_sync.backup_file(markdown_path)

            # Convert to PDF
            pdf_path = self.markdown_to_pdf.convert_markdown_to_pdf(markdown_path)
            self.stats["pdfs_generated"] += 1

            # Send to Kindle if enabled
            if self.config.get("sync.auto_send_to_kindle", True):
                success = self.kindle_sync.send_pdf_to_kindle(pdf_path)
                if success:
                    self.stats["pdfs_sent_to_kindle"] += 1
                else:
                    logger.warning(f"Failed to send {pdf_path.name} to Kindle")

            logger.info(f"Processed Markdown file: {markdown_path.name}")

        except Exception as e:
            logger.error(f"Error processing Markdown file {markdown_path}: {e}")
            raise

    def _process_pdf_file(self, pdf_path: Path):
        """Process a PDF file."""
        try:
            # Create backup
            self.kindle_sync.backup_file(pdf_path)

            # Convert to Markdown
            self.pdf_to_markdown.convert_pdf_to_markdown(pdf_path)
            self.stats["markdown_files_created"] += 1

            logger.info(f"Processed PDF file: {pdf_path.name}")

        except Exception as e:
            logger.error(f"Error processing PDF file {pdf_path}: {e}")
            raise

    def sync_from_kindle(self, kindle_path: Optional[Path] = None) -> int:
        """Sync documents from Kindle to Obsidian."""
        try:
            synced_files = self.kindle_sync.sync_from_kindle(kindle_path)

            # Process each synced file
            for file_path in synced_files:
                if file_path.suffix.lower() == ".pdf":
                    self._process_pdf_file(file_path)

            logger.info(f"Synced {len(synced_files)} files from Kindle")
            return len(synced_files)

        except Exception as e:
            logger.error(f"Error syncing from Kindle: {e}")
            return 0

    def get_statistics(self) -> Dict[str, Any]:
        """Get processing statistics."""
        return self.stats.copy()

    def reset_statistics(self):
        """Reset processing statistics."""
        self.stats = {
            "files_processed": 0,
            "pdfs_generated": 0,
            "pdfs_sent_to_kindle": 0,
            "markdown_files_created": 0,
            "errors": 0,
        }
        logger.info("Statistics reset")

    def cleanup_old_files(self, max_age_days: int = 30) -> int:
        """Clean up old files from sync and backup folders."""
        try:
            cleaned_count = 0

            # Clean sync folder
            sync_folder = self.config.get_sync_folder_path()
            if sync_folder.exists():
                cleaned_count += self.kindle_sync.cleanup_old_files(
                    sync_folder, max_age_days
                )

            # Clean backup folder
            backup_folder = self.config.get_backup_folder_path()
            if backup_folder.exists():
                cleaned_count += self.kindle_sync.cleanup_old_files(
                    backup_folder, max_age_days
                )

            logger.info(f"Cleaned up {cleaned_count} old files")
            return cleaned_count

        except Exception as e:
            logger.error(f"Error cleaning up old files: {e}")
            return 0
