"""
Async main application for Kindle Sync.

This module provides the main entry point for the async version of the
Kindle Sync application with database integration, monitoring, and
asynchronous file processing.
"""

import asyncio
import signal
import sys
from typing import Any, Optional

from loguru import logger
from pathlib import Path

from .config import Config
from .core.async_file_watcher import AsyncFileWatcher
from .core.async_processor import AsyncSyncProcessor
from .core.error_handler import ErrorHandler
from .core.exceptions import ErrorSeverity, KindleSyncError
from .database.manager import DatabaseManager
from .monitoring.health_checks import HealthChecker
from .monitoring.metrics import MetricsCollector
from .monitoring.prometheus_exporter import MetricsUpdater, PrometheusExporter


class AsyncKindleSyncApp:
    """Main async application class for Kindle Sync."""

    def __init__(self, config_path: Optional[Path] = None):
        self.config = Config(config_path)
        self.db_manager: Optional[DatabaseManager] = None
        self.processor: Optional[AsyncSyncProcessor] = None
        self.file_watcher: Optional[AsyncFileWatcher] = None
        self.health_checker: Optional[HealthChecker] = None
        self.metrics_collector: Optional[MetricsCollector] = None
        self.prometheus_exporter: Optional[PrometheusExporter] = None
        self.metrics_updater: Optional[MetricsUpdater] = None
        self.error_handler: Optional[ErrorHandler] = None
        self.prometheus_runner: Optional[object] = None
        self.running = False
        logger.info("AsyncKindleSyncApp initialized.")

    async def initialize(self):
        """Initialize all application components."""
        try:
            logger.info("Initializing AsyncKindleSyncApp components...")

            # Initialize error handler first
            self.error_handler = ErrorHandler(self.config)
            logger.info("Error handler initialized.")

            # Initialize database
            db_path = Path(self.config.get("database.path", "data/kindle_sync.db"))
            self.db_manager = DatabaseManager(db_path)
            logger.info("Database manager initialized.")

            # Initialize metrics collector
            self.metrics_collector = MetricsCollector()
            self.metrics_updater = MetricsUpdater(self.metrics_collector)
            logger.info("Metrics collector initialized.")

            # Initialize health checker
            self.health_checker = HealthChecker(self.config, self.db_manager)
            logger.info("Health checker initialized.")

            # Initialize async processor
            max_workers = self.config.get("advanced.async_workers", 3)
            self.processor = AsyncSyncProcessor(self.config, max_workers)
            logger.info("Async processor initialized.")

            # Initialize async file watcher
            self.file_watcher = AsyncFileWatcher(self.config, self.processor)
            logger.info("Async file watcher initialized.")

            # Initialize Prometheus exporter
            self.prometheus_exporter = PrometheusExporter(
                self.config,
                self.db_manager,
                self.metrics_collector,
                self.health_checker,
            )
            logger.info("Prometheus exporter initialized.")

            logger.info("All components initialized successfully.")
        except Exception as e:
            error = KindleSyncError(
                f"Failed to initialize application: {e}",
                severity=ErrorSeverity.CRITICAL,
            )
            if self.error_handler:
                self.error_handler.handle_error(error, {"component": "initialization"})
            raise error

    async def start(self) -> None:
        """Start the async application."""
        try:
            logger.info("Starting AsyncKindleSyncApp...")
            self.running = True

            # Run initial health check
            if self.health_checker:
                health_results = await self.health_checker.run_all_checks()
                if health_results["overall_status"] != "healthy":
                    logger.warning(f"Health check failed: {health_results}")
                    # Continue anyway, but log the issues

            # Start Prometheus exporter
            if self.prometheus_exporter:
                exporter_host = self.config.get("monitoring.exporter_host", "0.0.0.0")
                exporter_port = self.config.get("monitoring.exporter_port", 8080)
                self.prometheus_runner = await self.prometheus_exporter.start_server(
                    exporter_host, exporter_port
                )

            # Start file watcher (this will start the async processing workers)
            if self.file_watcher:
                await self.file_watcher.start()

        except Exception as e:
            error = KindleSyncError(
                f"Failed to start application: {e}", severity=ErrorSeverity.CRITICAL
            )
            if self.error_handler:
                self.error_handler.handle_error(error, {"component": "startup"})
            raise error

    async def stop(self) -> None:
        """Stop the async application gracefully."""
        try:
            logger.info("Stopping AsyncKindleSyncApp...")
            self.running = False

            # Stop file watcher
            if self.file_watcher:
                await self.file_watcher.stop()
                logger.info("File watcher stopped.")

            # Stop Prometheus exporter
            if self.prometheus_runner and self.prometheus_exporter:
                await self.prometheus_exporter.stop_server(self.prometheus_runner)
                logger.info("Prometheus exporter stopped.")

            # Shutdown processor
            if self.processor:
                await self.processor.cleanup()
                logger.info("Processor shut down.")

            # Close database connection
            if self.db_manager:
                self.db_manager.engine.dispose()
                logger.info("Database connection closed.")

            logger.info("AsyncKindleSyncApp stopped successfully.")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

    async def run_health_check_loop(self) -> None:
        """Run periodic health checks."""
        while self.running:
            try:
                await asyncio.sleep(60)  # Check every minute
                if self.running and self.health_checker:
                    health_results = await self.health_checker.run_all_checks()
                    if health_results["overall_status"] != "healthy":
                        logger.warning(f"Health check failed: {health_results}")
                        # Update metrics for health check failures
                        if self.metrics_updater:
                            self.metrics_updater.on_error(
                                "health_check_failure", "medium"
                            )
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
                if self.metrics_updater:
                    self.metrics_updater.on_error("health_check_error", "high")

    async def run_metrics_update_loop(self) -> None:
        """Run periodic metrics updates."""
        while self.running:
            try:
                await asyncio.sleep(30)  # Update every 30 seconds
                if self.running and self.file_watcher and self.metrics_updater:
                    # Update queue and task metrics
                    queue_size = self.file_watcher.processing_queue.qsize()
                    active_tasks = len(self.file_watcher.workers)
                    self.metrics_updater.update_queue_metrics(queue_size, active_tasks)
            except Exception as e:
                logger.error(f"Error in metrics update loop: {e}")

    def setup_signal_handlers(self) -> None:
        """Set up signal handlers for graceful shutdown."""

        def signal_handler(signum: int, frame: Any) -> None:
            logger.info(f"Received signal {signum}, initiating graceful shutdown...")
            asyncio.create_task(self.stop())

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        logger.info("Signal handlers set up.")

    async def run(self) -> None:
        """Main application run loop."""
        try:
            await self.initialize()
            self.setup_signal_handlers()

            # Start the main application
            await self.start()

            # Start background tasks
            health_task = asyncio.create_task(self.run_health_check_loop())
            metrics_task = asyncio.create_task(self.run_metrics_update_loop())

            logger.info("AsyncKindleSyncApp is running. Press Ctrl+C to stop.")

            # Keep the application running
            try:
                while self.running:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                logger.info("Received keyboard interrupt, shutting down...")
            finally:
                # Cancel background tasks
                health_task.cancel()
                metrics_task.cancel()
                await asyncio.gather(health_task, metrics_task, return_exceptions=True)

                # Stop the application
                await self.stop()

        except Exception as e:
            logger.error(f"Fatal error in main run loop: {e}")
            if self.error_handler:
                self.error_handler.handle_error(
                    KindleSyncError(
                        f"Fatal application error: {e}", severity=ErrorSeverity.CRITICAL
                    ),
                    {"component": "main_loop"},
                )
            raise


async def main() -> None:
    """Main entry point for the async application."""
    try:
        # Set up logging
        logger.remove()
        logger.add(
            sys.stderr,
            level="INFO",
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        )

        # Create and run the application
        app = AsyncKindleSyncApp()
        await app.run()

    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.error(f"Application failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
