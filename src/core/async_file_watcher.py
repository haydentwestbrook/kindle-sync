"""Asynchronous file watcher with queue-based processing."""

import asyncio
from datetime import datetime
from typing import Any
from collections.abc import Callable

from loguru import logger
from pathlib import Path
from watchdog.events import (
    FileCreatedEvent,
    FileModifiedEvent,
    FileMovedEvent,
    FileSystemEventHandler,
)
from watchdog.observers import Observer

from ..config import Config
from .async_processor import AsyncSyncProcessor


class AsyncFileHandler(FileSystemEventHandler):
    """File system event handler that adds files to async queue."""

    def __init__(
        self,
        processing_queue: asyncio.Queue,
        file_filter: Callable[[Path], bool] | None = None,
    ):
        """
        Initialize async file handler.

        Args:
            processing_queue: Async queue for file processing
            file_filter: Optional function to filter which files to process
        """
        self.processing_queue = processing_queue
        self.file_filter = file_filter or self._default_file_filter
        self.debounce_timers: dict[str, asyncio.Task] = {}
        self.debounce_delay = 1.0  # 1 second debounce

    def _default_file_filter(self, file_path: Path) -> bool:
        """Default file filter - only process .md and .pdf files."""
        return file_path.suffix.lower() in [".md", ".pdf"]

    def _should_process_file(self, file_path: Path) -> bool:
        """Check if file should be processed."""
        if not file_path.is_file():
            return False

        if not self.file_filter(file_path):
            return False

        # Skip temporary files
        if file_path.name.startswith(".") or file_path.name.startswith("~"):
            return False

        return True

    def _schedule_file_processing(self, file_path: Path):
        """Schedule file for processing with debouncing."""
        file_key = str(file_path)

        # Cancel existing timer if any
        if file_key in self.debounce_timers:
            self.debounce_timers[file_key].cancel()

        # Create new timer
        async def process_after_delay():
            try:
                await asyncio.sleep(self.debounce_delay)
                if self._should_process_file(file_path):
                    await self.processing_queue.put(file_path)
                    logger.info(f"Queued file for processing: {file_path}")
            except asyncio.CancelledError:
                pass
            finally:
                self.debounce_timers.pop(file_key, None)

        self.debounce_timers[file_key] = asyncio.create_task(process_after_delay())

    def on_modified(self, event):
        """Handle file modification events."""
        if isinstance(event, FileModifiedEvent):
            file_path = Path(event.src_path)
            self._schedule_file_processing(file_path)

    def on_created(self, event):
        """Handle file creation events."""
        if isinstance(event, FileCreatedEvent):
            file_path = Path(event.src_path)
            self._schedule_file_processing(file_path)

    def on_moved(self, event):
        """Handle file move events."""
        if isinstance(event, FileMovedEvent):
            # Process the destination file
            file_path = Path(event.dest_path)
            self._schedule_file_processing(file_path)


class AsyncFileWatcher:
    """Asynchronous file watcher with queue-based processing."""

    def __init__(
        self,
        config: Config,
        processor: AsyncSyncProcessor,
        max_workers: int = 3,
        debounce_delay: float = 1.0,
    ):
        """
        Initialize async file watcher.

        Args:
            config: Application configuration
            processor: Async processor for handling files
            max_workers: Number of concurrent processing workers
            debounce_delay: Delay in seconds before processing a file
        """
        self.config = config
        self.processor = processor
        self.max_workers = max_workers
        self.debounce_delay = debounce_delay

        self.observer: Observer | None = None
        self.processing_queue = asyncio.Queue(maxsize=1000)
        self.workers: list[asyncio.Task] = []
        self.running = False

        # Statistics
        self.stats = {
            "files_queued": 0,
            "files_processed": 0,
            "files_successful": 0,
            "files_failed": 0,
            "queue_size": 0,
            "active_workers": 0,
        }

        logger.info(f"Async file watcher initialized with {max_workers} workers")

    async def start(self, watch_path: Path | None = None):
        """
        Start async file watching.

        Args:
            watch_path: Path to watch (defaults to Obsidian vault path)
        """
        if self.running:
            logger.warning("File watcher is already running")
            return

        self.running = True

        # Determine watch path
        if watch_path is None:
            watch_path = self.config.get_obsidian_vault_path()

        if not watch_path.exists():
            logger.error(f"Watch path does not exist: {watch_path}")
            raise FileNotFoundError(f"Watch path does not exist: {watch_path}")

        # Start file system observer
        self.observer = Observer()
        handler = AsyncFileHandler(self.processing_queue, self._file_filter)
        self.observer.schedule(handler, str(watch_path), recursive=True)
        self.observer.start()

        # Start processing workers
        self.workers = [
            asyncio.create_task(self._process_queue_worker(f"worker-{i}"))
            for i in range(self.max_workers)
        ]

        logger.info(
            f"Started file watcher for {watch_path} with {self.max_workers} workers"
        )

        # Wait for workers to complete (they run indefinitely)
        try:
            await asyncio.gather(*self.workers)
        except asyncio.CancelledError:
            logger.info("File watcher workers cancelled")

    async def stop(self):
        """Stop the file watcher."""
        if not self.running:
            return

        self.running = False

        # Stop file system observer
        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.observer = None

        # Cancel all workers
        for worker in self.workers:
            worker.cancel()

        # Wait for workers to complete
        if self.workers:
            await asyncio.gather(*self.workers, return_exceptions=True)

        self.workers.clear()

        logger.info("File watcher stopped")

    async def _process_queue_worker(self, worker_name: str):
        """Process files from the queue (worker coroutine)."""
        logger.info(f"Started queue worker: {worker_name}")

        while self.running:
            try:
                # Get file from queue with timeout
                file_path = await asyncio.wait_for(
                    self.processing_queue.get(), timeout=1.0
                )

                self.stats["active_workers"] += 1
                self.stats["queue_size"] = self.processing_queue.qsize()

                try:
                    # Process the file
                    result = await self.processor.process_file_async(file_path)

                    # Update statistics
                    self.stats["files_processed"] += 1
                    if result.success:
                        self.stats["files_successful"] += 1
                    else:
                        self.stats["files_failed"] += 1

                    logger.info(
                        f"{worker_name} processed {file_path}: {result.success}"
                    )

                except Exception as e:
                    logger.error(f"{worker_name} error processing {file_path}: {e}")
                    self.stats["files_processed"] += 1
                    self.stats["files_failed"] += 1

                finally:
                    self.stats["active_workers"] -= 1
                    self.stats["queue_size"] = self.processing_queue.qsize()
                    self.processing_queue.task_done()

            except TimeoutError:
                # No files in queue, continue
                continue
            except Exception as e:
                logger.error(f"{worker_name} unexpected error: {e}")
                await asyncio.sleep(1)  # Brief pause before retrying

        logger.info(f"Queue worker {worker_name} stopped")

    def _file_filter(self, file_path: Path) -> bool:
        """Filter files to determine which ones to process."""
        # Only process .md and .pdf files
        if file_path.suffix.lower() not in [".md", ".pdf"]:
            return False

        # Skip hidden files
        if file_path.name.startswith("."):
            return False

        # Skip temporary files
        if file_path.name.startswith("~") or file_path.name.endswith(".tmp"):
            return False

        # Check file size limits
        try:
            max_size = (
                self.config.get("processing.max_file_size", 50) * 1024 * 1024
            )  # Convert MB to bytes
            if file_path.stat().st_size > max_size:
                logger.warning(f"File {file_path} exceeds size limit, skipping")
                return False
        except OSError:
            # File might have been deleted
            return False

        return True

    async def add_file_manually(self, file_path: Path, priority: int = 0):
        """Manually add a file to the processing queue."""
        if not self._file_filter(file_path):
            logger.warning(
                f"File {file_path} does not pass filter, not adding to queue"
            )
            return False

        try:
            await self.processing_queue.put(file_path)
            self.stats["files_queued"] += 1
            self.stats["queue_size"] = self.processing_queue.qsize()
            logger.info(f"Manually queued file: {file_path}")
            return True
        except asyncio.QueueFull:
            logger.error(f"Processing queue is full, cannot add {file_path}")
            return False

    def get_statistics(self) -> dict[str, Any]:
        """Get file watcher statistics."""
        return {
            **self.stats,
            "running": self.running,
            "observer_alive": self.observer.is_alive() if self.observer else False,
            "max_workers": self.max_workers,
        }

    def get_health_status(self) -> dict[str, Any]:
        """Get health status of the file watcher."""
        return {
            "running": self.running,
            "observer_alive": self.observer.is_alive() if self.observer else False,
            "active_workers": self.stats["active_workers"],
            "queue_size": self.stats["queue_size"],
            "max_workers": self.max_workers,
            "queue_full": self.processing_queue.full(),
            "last_activity": datetime.utcnow().isoformat(),
        }

    async def process_existing_files(
        self, watch_path: Path | None = None, max_files: int = 100
    ):
        """
        Process existing files in the watch directory.

        Args:
            watch_path: Path to scan for files
            max_files: Maximum number of files to process
        """
        if watch_path is None:
            watch_path = self.config.get_obsidian_vault_path()

        if not watch_path.exists():
            logger.error(f"Watch path does not exist: {watch_path}")
            return 0

        processed_count = 0

        # Find all markdown and PDF files
        for file_path in watch_path.rglob("*"):
            if processed_count >= max_files:
                break

            if self._file_filter(file_path):
                success = await self.add_file_manually(file_path)
                if success:
                    processed_count += 1

        logger.info(f"Queued {processed_count} existing files for processing")
        return processed_count
