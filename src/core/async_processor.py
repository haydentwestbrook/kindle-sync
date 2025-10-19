"""Asynchronous file processing with thread pool and queue management."""

import asyncio
import hashlib
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from loguru import logger
from pathlib import Path

from ..config import Config

try:
    from ..database import DatabaseManager
    from ..database.models import ProcessingStatus

    DATABASE_AVAILABLE = True
except ImportError:
    DatabaseManager = None
    ProcessingStatus = None
    DATABASE_AVAILABLE = False
from ..security.validation import FileValidationRequest, FileValidator


@dataclass
class ProcessingResult:
    """Result of file processing operation."""

    success: bool
    file_path: Path
    processing_time_ms: int | None = None
    error_message: str | None = None
    output_path: Path | None = None
    metadata: dict[str, Any] | None = None


class AsyncSyncProcessor:
    """Asynchronous file processing with thread pool and queue management."""

    def __init__(self, config: Config, max_workers: int = 4):
        """
        Initialize async processor.

        Args:
            config: Application configuration
            max_workers: Maximum number of worker threads
        """
        self.config = config
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.processing_queue = asyncio.Queue(maxsize=1000)
        self.active_tasks: dict[str, asyncio.Task] = {}
        self.file_validator = FileValidator()

        # Initialize database manager
        if DATABASE_AVAILABLE:
            db_path = Path(config.get("database.path", "kindle_sync.db"))
            self.db_manager = DatabaseManager(db_path)
        else:
            self.db_manager = None

        # Statistics
        self.stats = {
            "files_processed": 0,
            "files_successful": 0,
            "files_failed": 0,
            "total_processing_time_ms": 0,
            "active_tasks": 0,
            "queue_size": 0,
        }

        logger.info(f"Async processor initialized with {max_workers} workers")

    async def process_file_async(
        self, file_path: Path, priority: int = 0
    ) -> ProcessingResult:
        """
        Process file asynchronously.

        Args:
            file_path: Path to the file to process
            priority: Processing priority (higher = more important)

        Returns:
            ProcessingResult with processing outcome
        """
        start_time = datetime.utcnow()
        task_id = f"{file_path.name}_{file_path.stat().st_mtime}"

        try:
            # Check if already processing
            if task_id in self.active_tasks:
                return ProcessingResult(
                    success=False,
                    file_path=file_path,
                    error_message="File already being processed",
                )

            # Validate file
            validation_request = FileValidationRequest(
                file_path=file_path,
                max_size_mb=self.config.get("processing.max_file_size", 50),
            )
            validation_result = self.file_validator.validate_file(validation_request)

            if not validation_result.valid:
                error_msg = f"File validation failed: {validation_result.error}"
                await self._record_processing_result(
                    file_path, ProcessingStatus.FAILED, error_message=error_msg
                )
                return ProcessingResult(
                    success=False, file_path=file_path, error_message=error_msg
                )

            # Calculate file hash
            file_hash = self._calculate_file_hash(file_path)

            # Check if file was already processed successfully
            existing = self.db_manager.get_file_processing_history(str(file_path))
            if (
                existing
                and existing.status == ProcessingStatus.SUCCESS
                and existing.file_hash == file_hash
            ):
                logger.info(
                    f"File {file_path} already processed successfully, skipping"
                )
                return ProcessingResult(
                    success=True,
                    file_path=file_path,
                    metadata={"skipped": True, "reason": "already_processed"},
                )

            # Create processing task
            task = asyncio.create_task(
                self._process_file_with_retry(file_path, file_hash)
            )
            self.active_tasks[task_id] = task
            self.stats["active_tasks"] = len(self.active_tasks)

            try:
                result = await task
                return result
            finally:
                self.active_tasks.pop(task_id, None)
                self.stats["active_tasks"] = len(self.active_tasks)

        except Exception as e:
            error_msg = f"Unexpected error processing file: {e}"
            logger.error(error_msg)
            await self._record_processing_result(
                file_path, ProcessingStatus.FAILED, error_message=error_msg
            )
            return ProcessingResult(
                success=False, file_path=file_path, error_message=error_msg
            )
        finally:
            # Update processing time
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            self.stats["total_processing_time_ms"] += processing_time

    async def _process_file_with_retry(
        self, file_path: Path, file_hash: str
    ) -> ProcessingResult:
        """Process file with retry logic."""
        max_retries = self.config.get("processing.max_retries", 3)

        for attempt in range(max_retries):
            try:
                result = await self._process_file_sync(file_path, file_hash)
                if result.success:
                    return result
                elif attempt < max_retries - 1:
                    wait_time = 2**attempt  # Exponential backoff
                    logger.warning(
                        f"Processing failed, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    return result
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = 2**attempt
                    logger.warning(f"Processing error, retrying in {wait_time}s: {e}")
                    await asyncio.sleep(wait_time)
                else:
                    error_msg = f"Processing failed after {max_retries} attempts: {e}"
                    await self._record_processing_result(
                        file_path,
                        ProcessingStatus.FAILED,
                        error_message=error_msg,
                        retry_count=max_retries,
                    )
                    return ProcessingResult(
                        success=False, file_path=file_path, error_message=error_msg
                    )

        return ProcessingResult(
            success=False, file_path=file_path, error_message="Max retries exceeded"
        )

    async def _process_file_sync(
        self, file_path: Path, file_hash: str
    ) -> ProcessingResult:
        """Process file using thread pool for CPU-bound operations."""
        loop = asyncio.get_event_loop()
        start_time = datetime.utcnow()

        try:
            # Record processing start
            await self._record_processing_result(
                file_path, ProcessingStatus.PROCESSING, retry_count=0
            )

            if file_path.suffix.lower() == ".md":
                # Process markdown file
                result = await self._process_markdown_file(file_path, file_hash, loop)
            elif file_path.suffix.lower() == ".pdf":
                # Process PDF file
                result = await self._process_pdf_file(file_path, file_hash, loop)
            else:
                error_msg = f"Unsupported file type: {file_path.suffix}"
                await self._record_processing_result(
                    file_path, ProcessingStatus.FAILED, error_message=error_msg
                )
                return ProcessingResult(
                    success=False, file_path=file_path, error_message=error_msg
                )

            # Update statistics
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            self.stats["files_processed"] += 1

            if result.success:
                self.stats["files_successful"] += 1
                await self._record_processing_result(
                    file_path,
                    ProcessingStatus.SUCCESS,
                    processing_time_ms=int(processing_time),
                )
            else:
                self.stats["files_failed"] += 1
                await self._record_processing_result(
                    file_path,
                    ProcessingStatus.FAILED,
                    processing_time_ms=int(processing_time),
                    error_message=result.error_message,
                )

            result.processing_time_ms = int(processing_time)
            return result

        except Exception as e:
            error_msg = f"Error processing file: {e}"
            logger.error(error_msg)
            await self._record_processing_result(
                file_path, ProcessingStatus.FAILED, error_message=error_msg
            )
            return ProcessingResult(
                success=False, file_path=file_path, error_message=error_msg
            )

    async def _process_markdown_file(
        self, file_path: Path, file_hash: str, loop: asyncio.AbstractEventLoop
    ) -> ProcessingResult:
        """Process markdown file (convert to PDF and send to Kindle)."""
        try:
            # Import here to avoid circular imports
            from ..kindle_sync import KindleSync
            from ..pdf_converter import MarkdownToPDFConverter

            # Initialize converters
            pdf_converter = MarkdownToPDFConverter(self.config)
            kindle_sync = KindleSync(self.config)

            # Convert markdown to PDF (CPU-bound operation)
            pdf_path = await loop.run_in_executor(
                self.executor,
                self._convert_markdown_to_pdf_sync,
                pdf_converter,
                file_path,
            )

            # Record conversion operation
            file_id = await self._get_file_id(file_path)
            if file_id:
                self.db_manager.record_file_operation(
                    file_id, "convert_markdown_to_pdf", ProcessingStatus.SUCCESS
                )

            # Send to Kindle (I/O-bound operation)
            success = await self._send_pdf_to_kindle_async(kindle_sync, pdf_path, loop)

            # Record send operation
            if file_id:
                self.db_manager.record_file_operation(
                    file_id,
                    "send_to_kindle",
                    ProcessingStatus.SUCCESS if success else ProcessingStatus.FAILED,
                )

            return ProcessingResult(
                success=success,
                file_path=file_path,
                output_path=pdf_path,
                metadata={"converted_to_pdf": True, "sent_to_kindle": success},
            )

        except Exception as e:
            return ProcessingResult(
                success=False,
                file_path=file_path,
                error_message=f"Markdown processing failed: {e}",
            )

    async def _process_pdf_file(
        self, file_path: Path, file_hash: str, loop: asyncio.AbstractEventLoop
    ) -> ProcessingResult:
        """Process PDF file (convert to markdown)."""
        try:
            # Import here to avoid circular imports
            from ..pdf_converter import PDFToMarkdownConverter

            # Initialize converter
            pdf_converter = PDFToMarkdownConverter(self.config)

            # Convert PDF to markdown (CPU-bound operation)
            markdown_path = await loop.run_in_executor(
                self.executor,
                self._convert_pdf_to_markdown_sync,
                pdf_converter,
                file_path,
            )

            # Record conversion operation
            file_id = await self._get_file_id(file_path)
            if file_id:
                self.db_manager.record_file_operation(
                    file_id, "convert_pdf_to_markdown", ProcessingStatus.SUCCESS
                )

            return ProcessingResult(
                success=True,
                file_path=file_path,
                output_path=markdown_path,
                metadata={"converted_to_markdown": True},
            )

        except Exception as e:
            return ProcessingResult(
                success=False,
                file_path=file_path,
                error_message=f"PDF processing failed: {e}",
            )

    def _convert_markdown_to_pdf_sync(self, converter, file_path: Path) -> Path:
        """Synchronous markdown to PDF conversion."""
        return converter.convert_markdown_to_pdf(file_path)

    def _convert_pdf_to_markdown_sync(self, converter, file_path: Path) -> Path:
        """Synchronous PDF to markdown conversion."""
        return converter.convert_pdf_to_markdown(file_path)

    async def _send_pdf_to_kindle_async(
        self, kindle_sync, pdf_path: Path, loop: asyncio.AbstractEventLoop
    ) -> bool:
        """Send PDF to Kindle asynchronously."""
        try:
            return await loop.run_in_executor(
                self.executor, kindle_sync.send_pdf_to_kindle, pdf_path
            )
        except Exception as e:
            logger.error(f"Failed to send PDF to Kindle: {e}")
            return False

    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of file."""
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    async def _record_processing_result(
        self,
        file_path: Path,
        status: ProcessingStatus,
        processing_time_ms: int | None = None,
        error_message: str | None = None,
        retry_count: int = 0,
    ):
        """Record processing result in database."""
        try:
            file_hash = self._calculate_file_hash(file_path)
            file_size = file_path.stat().st_size
            file_type = file_path.suffix

            self.db_manager.record_file_processing(
                str(file_path),
                file_hash,
                file_size,
                file_type,
                status,
                processing_time_ms,
                error_message,
                retry_count,
            )
        except Exception as e:
            logger.error(f"Failed to record processing result: {e}")

    async def _get_file_id(self, file_path: Path) -> int | None:
        """Get file ID from database."""
        try:
            file_record = self.db_manager.get_file_processing_history(str(file_path))
            return file_record.id if file_record else None
        except Exception as e:
            logger.error(f"Failed to get file ID: {e}")
            return None

    # Queue management methods

    async def add_to_queue(
        self,
        file_path: Path,
        priority: int = 0,
        scheduled_for: datetime | None = None,
    ):
        """Add file to processing queue."""
        try:
            file_hash = self._calculate_file_hash(file_path)
            self.db_manager.add_to_queue(
                str(file_path), file_hash, priority, scheduled_for
            )
            self.stats["queue_size"] = self.db_manager.get_queue_size()
            logger.info(
                f"Added {file_path} to processing queue with priority {priority}"
            )
        except Exception as e:
            logger.error(f"Failed to add file to queue: {e}")

    async def process_queue(self, max_items: int = 10):
        """Process items from the queue."""
        processed_count = 0

        for _ in range(max_items):
            queue_item = self.db_manager.get_next_queue_item()
            if not queue_item:
                break

            file_path = Path(queue_item.file_path)
            if not file_path.exists():
                logger.warning(
                    f"File {file_path} no longer exists, removing from queue"
                )
                self.db_manager.remove_from_queue(str(file_path))
                continue

            # Process the file
            result = await self.process_file_async(file_path, queue_item.priority)

            # Remove from queue
            self.db_manager.remove_from_queue(str(file_path))
            processed_count += 1

            logger.info(
                f"Processed queue item: {file_path} - Success: {result.success}"
            )

        self.stats["queue_size"] = self.db_manager.get_queue_size()
        return processed_count

    # Statistics and monitoring

    def get_statistics(self) -> dict[str, Any]:
        """Get processing statistics."""
        db_stats = self.db_manager.get_processing_statistics()

        return {
            **self.stats,
            "database_stats": db_stats,
            "average_processing_time_ms": (
                self.stats["total_processing_time_ms"]
                / max(self.stats["files_processed"], 1)
            ),
        }

    def get_health_status(self) -> dict[str, Any]:
        """Get health status of the processor."""
        return {
            "active_tasks": len(self.active_tasks),
            "queue_size": self.stats["queue_size"],
            "max_workers": self.max_workers,
            "database_connected": True,  # TODO: Add actual database health check
            "last_processed": datetime.utcnow().isoformat(),
        }

    async def cleanup(self):
        """Cleanup resources."""
        # Cancel all active tasks
        for task in self.active_tasks.values():
            task.cancel()

        # Wait for tasks to complete
        if self.active_tasks:
            await asyncio.gather(*self.active_tasks.values(), return_exceptions=True)

        # Shutdown executor
        self.executor.shutdown(wait=True)

        logger.info("Async processor cleanup completed")
