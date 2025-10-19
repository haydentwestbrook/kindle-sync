"""
Prometheus metrics exporter for Kindle Sync application.

This module provides a web server that exposes application metrics
in Prometheus format for monitoring and alerting.
"""

import asyncio
import json
from typing import Any, Dict, Optional

from aiohttp import ClientSession, web
from aiohttp.web import Request, Response
from loguru import logger
from pathlib import Path

from ..config import Config
from ..core.exceptions import ErrorSeverity, MonitoringError
from ..database.manager import DatabaseManager
from .health_checks import HealthChecker
from .metrics import MetricsCollector


class PrometheusExporter:
    """Prometheus metrics exporter with health check endpoints."""

    def __init__(
        self,
        config: Config,
        db_manager: DatabaseManager,
        metrics_collector: MetricsCollector,
        health_checker: HealthChecker,
    ):
        self.config = config
        self.db_manager = db_manager
        self.metrics_collector = metrics_collector
        self.health_checker = health_checker
        self.app = web.Application()
        self._setup_routes()
        self._setup_middleware()
        logger.info("PrometheusExporter initialized.")

    def _setup_routes(self):
        """Set up HTTP routes for metrics and health checks."""
        self.app.router.add_get("/metrics", self._metrics_handler)
        self.app.router.add_get("/health", self._health_handler)
        self.app.router.add_get("/health/ready", self._readiness_handler)
        self.app.router.add_get("/health/live", self._liveness_handler)
        self.app.router.add_get("/status", self._status_handler)
        logger.info("HTTP routes configured.")

    def _setup_middleware(self):
        """Set up middleware for request logging and error handling."""

        @web.middleware
        async def error_middleware(request: Request, handler):
            try:
                return await handler(request)
            except Exception as e:
                logger.error(f"Error in {request.path}: {e}")
                return web.json_response(
                    {"error": "Internal server error", "message": str(e)}, status=500
                )

        @web.middleware
        async def logging_middleware(request: Request, handler):
            start_time = asyncio.get_event_loop().time()
            response = await handler(request)
            duration = asyncio.get_event_loop().time() - start_time
            logger.info(
                f"{request.method} {request.path} - {response.status} ({duration:.3f}s)"
            )
            return response

        self.app.middlewares.append(error_middleware)
        self.app.middlewares.append(logging_middleware)

    async def _metrics_handler(self, request: Request) -> Response:
        """Handle /metrics endpoint for Prometheus scraping."""
        try:
            # Update queue and task metrics
            self._update_dynamic_metrics()

            # Generate Prometheus format metrics
            metrics_data = self.metrics_collector.get_latest_metrics()

            return Response(
                body=metrics_data,
                content_type="text/plain; version=0.0.4; charset=utf-8",
            )
        except Exception as e:
            logger.error(f"Error generating metrics: {e}")
            raise MonitoringError(
                f"Failed to generate metrics: {e}", severity=ErrorSeverity.MEDIUM
            )

    async def _health_handler(self, request: Request) -> Response:
        """Handle /health endpoint for overall health status."""
        try:
            health_results = self.health_checker.run_all_checks()
            status_code = 200 if health_results["overall_status"] == "healthy" else 503

            return web.json_response(health_results, status=status_code)
        except Exception as e:
            logger.error(f"Error running health checks: {e}")
            return web.json_response(
                {"overall_status": "error", "error": str(e)}, status=500
            )

    async def _readiness_handler(self, request: Request) -> Response:
        """Handle /health/ready endpoint for Kubernetes readiness probe."""
        try:
            # Check critical dependencies
            checks = {
                "database": self._check_database_readiness(),
                "config_paths": self._check_config_readiness(),
                "email_config": self._check_email_readiness(),
            }

            all_ready = all(checks.values())
            status_code = 200 if all_ready else 503

            return web.json_response(
                {"ready": all_ready, "checks": checks}, status=status_code
            )
        except Exception as e:
            logger.error(f"Error checking readiness: {e}")
            return web.json_response({"ready": False, "error": str(e)}, status=500)

    async def _liveness_handler(self, request: Request) -> Response:
        """Handle /health/live endpoint for Kubernetes liveness probe."""
        try:
            # Simple liveness check - just verify the application is responding
            return web.json_response(
                {"alive": True, "timestamp": asyncio.get_event_loop().time()}
            )
        except Exception as e:
            logger.error(f"Error in liveness check: {e}")
            return web.json_response({"alive": False, "error": str(e)}, status=500)

    async def _status_handler(self, request: Request) -> Response:
        """Handle /status endpoint for detailed application status."""
        try:
            # Get comprehensive status information
            status_info = {
                "application": "kindle-sync",
                "version": "2.0.0",
                "uptime": asyncio.get_event_loop().time(),  # Simplified uptime
                "health": self.health_checker.run_all_checks(),
                "database_stats": await self._get_database_stats(),
                "config_summary": self._get_config_summary(),
            }

            return web.json_response(status_info)
        except Exception as e:
            logger.error(f"Error generating status: {e}")
            return web.json_response(
                {"error": "Failed to generate status", "message": str(e)}, status=500
            )

    def _update_dynamic_metrics(self):
        """Update metrics that change dynamically."""
        try:
            # Update queue size (if we have access to the async processor)
            # This would need to be passed in or accessed through a shared state
            # For now, we'll set it to 0 as a placeholder
            self.metrics_collector.set_queue_size(0)
            self.metrics_collector.set_active_tasks(0)
        except Exception as e:
            logger.warning(f"Failed to update dynamic metrics: {e}")

    def _check_database_readiness(self) -> bool:
        """Check if database is ready for operations."""
        try:
            with self.db_manager.get_session() as session:
                # Simple query to test connection
                session.execute("SELECT 1")
            return True
        except Exception as e:
            logger.warning(f"Database readiness check failed: {e}")
            return False

    def _check_config_readiness(self) -> bool:
        """Check if configuration paths are ready."""
        try:
            vault_path = self.config.get_obsidian_vault_path()
            sync_path = self.config.get_sync_folder_path()
            return vault_path.exists() and sync_path.exists()
        except Exception as e:
            logger.warning(f"Config readiness check failed: {e}")
            return False

    def _check_email_readiness(self) -> bool:
        """Check if email configuration is ready."""
        try:
            smtp_config = self.config.get_smtp_config()
            kindle_email = self.config.get_kindle_email()
            return all(
                [
                    smtp_config.get("server"),
                    smtp_config.get("username"),
                    smtp_config.get("password"),
                    kindle_email,
                ]
            )
        except Exception as e:
            logger.warning(f"Email readiness check failed: {e}")
            return False

    async def _get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        try:
            with self.db_manager.get_session() as session:
                # Get counts of processed files by status
                total_files = session.query(self.db_manager.ProcessedFile).count()
                successful_files = (
                    session.query(self.db_manager.ProcessedFile)
                    .filter_by(status="success")
                    .count()
                )
                failed_files = (
                    session.query(self.db_manager.ProcessedFile)
                    .filter_by(status="failed")
                    .count()
                )

                return {
                    "total_files": total_files,
                    "successful_files": successful_files,
                    "failed_files": failed_files,
                    "success_rate": (successful_files / total_files * 100)
                    if total_files > 0
                    else 0,
                }
        except Exception as e:
            logger.warning(f"Failed to get database stats: {e}")
            return {"error": str(e)}

    def _get_config_summary(self) -> Dict[str, Any]:
        """Get configuration summary (without sensitive data)."""
        try:
            return {
                "vault_path": str(self.config.get_obsidian_vault_path()),
                "sync_folder": str(self.config.get_sync_folder_path()),
                "backup_folder": str(self.config.get_backup_folder_path()),
                "kindle_email": self.config.get_kindle_email(),
                "smtp_server": self.config.get_smtp_config().get("server"),
                "async_workers": self.config.get("advanced.async_workers", 3),
                "max_file_size_mb": self.config.get("advanced.max_file_size_mb", 50),
                "retry_attempts": self.config.get("advanced.retry_attempts", 3),
            }
        except Exception as e:
            logger.warning(f"Failed to get config summary: {e}")
            return {"error": str(e)}

    async def start_server(self, host: str = "0.0.0.0", port: int = 8080):
        """Start the Prometheus exporter web server."""
        try:
            runner = web.AppRunner(self.app)
            await runner.setup()
            site = web.TCPSite(runner, host, port)
            await site.start()
            logger.info(f"Prometheus exporter started on http://{host}:{port}")
            logger.info("Available endpoints:")
            logger.info("  GET /metrics - Prometheus metrics")
            logger.info("  GET /health - Overall health status")
            logger.info("  GET /health/ready - Readiness probe")
            logger.info("  GET /health/live - Liveness probe")
            logger.info("  GET /status - Detailed application status")
            return runner
        except Exception as e:
            raise MonitoringError(
                f"Failed to start Prometheus exporter: {e}",
                severity=ErrorSeverity.CRITICAL,
            )

    async def stop_server(self, runner: web.AppRunner):
        """Stop the Prometheus exporter web server."""
        try:
            await runner.cleanup()
            logger.info("Prometheus exporter stopped.")
        except Exception as e:
            logger.error(f"Error stopping Prometheus exporter: {e}")


class MetricsUpdater:
    """Updates metrics based on application events."""

    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics_collector = metrics_collector
        logger.info("MetricsUpdater initialized.")

    def on_file_processed(
        self, file_path: Path, success: bool, file_type: str, processing_time_ms: int
    ):
        """Update metrics when a file is processed."""
        try:
            status = "success" if success else "failed"
            self.metrics_collector.increment_files_processed(status, file_type)
            self.metrics_collector.observe_file_processing_duration(
                processing_time_ms / 1000.0, file_type
            )
            logger.debug(
                f"Updated metrics for processed file: {file_path.name} ({status})"
            )
        except Exception as e:
            logger.warning(f"Failed to update file processing metrics: {e}")

    def on_pdf_generated(self):
        """Update metrics when a PDF is generated."""
        try:
            self.metrics_collector.increment_pdfs_generated()
            logger.debug("Updated metrics for PDF generation")
        except Exception as e:
            logger.warning(f"Failed to update PDF generation metrics: {e}")

    def on_pdf_sent(self, success: bool):
        """Update metrics when a PDF is sent to Kindle."""
        try:
            status = "success" if success else "failed"
            self.metrics_collector.increment_pdfs_sent(status)
            logger.debug(f"Updated metrics for PDF sending ({status})")
        except Exception as e:
            logger.warning(f"Failed to update PDF sending metrics: {e}")

    def on_markdown_created(self):
        """Update metrics when a Markdown file is created."""
        try:
            self.metrics_collector.increment_markdown_created()
            logger.debug("Updated metrics for Markdown creation")
        except Exception as e:
            logger.warning(f"Failed to update Markdown creation metrics: {e}")

    def on_error(self, error_type: str, severity: str):
        """Update metrics when an error occurs."""
        try:
            self.metrics_collector.increment_errors(error_type, severity)
            logger.debug(f"Updated metrics for error: {error_type} ({severity})")
        except Exception as e:
            logger.warning(f"Failed to update error metrics: {e}")

    def update_queue_metrics(self, queue_size: int, active_tasks: int):
        """Update queue and task metrics."""
        try:
            self.metrics_collector.set_queue_size(queue_size)
            self.metrics_collector.set_active_tasks(active_tasks)
            logger.debug(
                f"Updated queue metrics: size={queue_size}, active_tasks={active_tasks}"
            )
        except Exception as e:
            logger.warning(f"Failed to update queue metrics: {e}")
