"""Metrics collection and monitoring system."""

import asyncio
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from unittest.mock import Mock

from loguru import logger

from ..config import Config

try:
    from ..database import DatabaseManager

    DATABASE_AVAILABLE = True
except ImportError:
    DatabaseManager = None
    DATABASE_AVAILABLE = False


@dataclass
class Metric:
    """A single metric measurement."""

    name: str
    value: float
    timestamp: datetime
    tags: dict[str, str] = field(default_factory=dict)
    unit: str | None = None


class MetricsCollector:
    """Collects and manages application metrics."""

    def __init__(
        self,
        config: Config | None = None,
        db_manager: DatabaseManager | None = None,
    ):
        """
        Initialize metrics collector.

        Args:
            config: Application configuration
            db_manager: Optional database manager for persistence
        """
        self.config = config or Mock()
        self.db_manager = db_manager if DATABASE_AVAILABLE else None

        # In-memory metrics storage
        self.metrics: dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.counters: dict[str, float] = defaultdict(float)
        self.gauges: dict[str, float] = defaultdict(float)
        self.histograms: dict[str, list[float]] = defaultdict(list)

        # Collection settings
        self.collection_interval = config.get(
            "monitoring.metrics_interval", 60
        )  # seconds
        self.retention_days = config.get("monitoring.metrics_retention_days", 7)

        # Background collection task
        self.collection_task: asyncio.Task | None = None
        self.running = False

        logger.info("Metrics collector initialized")

    async def start(self):
        """Start background metrics collection."""
        if self.running:
            logger.warning("Metrics collector is already running")
            return

        self.running = True
        self.collection_task = asyncio.create_task(self._collection_loop())
        logger.info("Started metrics collection")

    async def stop(self):
        """Stop background metrics collection."""
        if not self.running:
            return

        self.running = False

        if self.collection_task:
            self.collection_task.cancel()
            try:
                await self.collection_task
            except asyncio.CancelledError:
                pass

        logger.info("Stopped metrics collection")

    async def _collection_loop(self):
        """Background loop for collecting system metrics."""
        while self.running:
            try:
                await self._collect_system_metrics()
                await asyncio.sleep(self.collection_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in metrics collection loop: {e}")
                await asyncio.sleep(5)  # Brief pause before retrying

    async def _collect_system_metrics(self):
        """Collect system-level metrics."""
        try:
            # CPU usage
            await self._collect_cpu_metrics()

            # Memory usage
            await self._collect_memory_metrics()

            # Disk usage
            await self._collect_disk_metrics()

            # File system metrics
            await self._collect_filesystem_metrics()

        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")

    async def _collect_cpu_metrics(self):
        """Collect CPU usage metrics."""
        try:
            import psutil

            # CPU percentage
            cpu_percent = psutil.cpu_percent(interval=1)
            self.record_gauge("system.cpu.percent", cpu_percent, unit="percent")

            # CPU count
            cpu_count = psutil.cpu_count()
            self.record_gauge("system.cpu.count", cpu_count, unit="cores")

            # Load average (Unix-like systems)
            if hasattr(psutil, "getloadavg"):
                load_avg = psutil.getloadavg()
                self.record_gauge("system.load.1min", load_avg[0])
                self.record_gauge("system.load.5min", load_avg[1])
                self.record_gauge("system.load.15min", load_avg[2])

        except ImportError:
            logger.debug("psutil not available for CPU metrics")
        except Exception as e:
            logger.error(f"Error collecting CPU metrics: {e}")

    async def _collect_memory_metrics(self):
        """Collect memory usage metrics."""
        try:
            import psutil

            memory = psutil.virtual_memory()

            # Memory percentages
            self.record_gauge("system.memory.percent", memory.percent, unit="percent")
            self.record_gauge(
                "system.memory.available.percent",
                (memory.available / memory.total) * 100,
                unit="percent",
            )

            # Memory in bytes
            self.record_gauge("system.memory.total", memory.total, unit="bytes")
            self.record_gauge("system.memory.available", memory.available, unit="bytes")
            self.record_gauge("system.memory.used", memory.used, unit="bytes")
            self.record_gauge("system.memory.free", memory.free, unit="bytes")

            # Swap memory
            swap = psutil.swap_memory()
            self.record_gauge("system.swap.percent", swap.percent, unit="percent")
            self.record_gauge("system.swap.total", swap.total, unit="bytes")
            self.record_gauge("system.swap.used", swap.used, unit="bytes")
            self.record_gauge("system.swap.free", swap.free, unit="bytes")

        except ImportError:
            logger.debug("psutil not available for memory metrics")
        except Exception as e:
            logger.error(f"Error collecting memory metrics: {e}")

    async def _collect_disk_metrics(self):
        """Collect disk usage metrics."""
        try:
            import shutil

            vault_path = self.config.get_obsidian_vault_path()

            # Disk usage for vault path
            total, used, free = shutil.disk_usage(vault_path)

            self.record_gauge("system.disk.total", total, unit="bytes")
            self.record_gauge("system.disk.used", used, unit="bytes")
            self.record_gauge("system.disk.free", free, unit="bytes")
            self.record_gauge(
                "system.disk.percent", (used / total) * 100, unit="percent"
            )

        except Exception as e:
            logger.error(f"Error collecting disk metrics: {e}")

    async def _collect_filesystem_metrics(self):
        """Collect file system specific metrics."""
        try:
            vault_path = self.config.get_obsidian_vault_path()

            if not vault_path.exists():
                return

            # Count files by type
            file_counts = defaultdict(int)
            total_size = 0

            for file_path in vault_path.rglob("*"):
                if file_path.is_file():
                    suffix = file_path.suffix.lower()
                    file_counts[suffix] += 1
                    total_size += file_path.stat().st_size

            # Record file counts
            for suffix, count in file_counts.items():
                self.record_gauge(
                    "filesystem.files.count",
                    count,
                    tags={"type": suffix or "no_extension"},
                )

            # Record total size
            self.record_gauge("filesystem.files.total_size", total_size, unit="bytes")

        except Exception as e:
            logger.error(f"Error collecting filesystem metrics: {e}")

    # Metric recording methods

    def record_counter(
        self, name: str, value: float = 1.0, tags: dict[str, str] | None = None
    ):
        """Record a counter metric (monotonically increasing)."""
        self.counters[name] += value
        self._record_metric(name, value, tags, "counter")

    def record_gauge(
        self,
        name: str,
        value: float,
        tags: dict[str, str] | None = None,
        unit: str | None = None,
    ):
        """Record a gauge metric (can go up or down)."""
        self.gauges[name] = value
        self._record_metric(name, value, tags, "gauge", unit)

    def record_histogram(
        self, name: str, value: float, tags: dict[str, str] | None = None
    ):
        """Record a histogram metric (distribution of values)."""
        self.histograms[name].append(value)
        # Keep only recent values (last 1000)
        if len(self.histograms[name]) > 1000:
            self.histograms[name] = self.histograms[name][-1000:]

        self._record_metric(name, value, tags, "histogram")

    def record_timing(
        self, name: str, duration_ms: float, tags: dict[str, str] | None = None
    ):
        """Record a timing metric (duration in milliseconds)."""
        self.record_histogram(name, duration_ms, tags)
        self._record_metric(name, duration_ms, tags, "timing", "ms")

    def _record_metric(
        self,
        name: str,
        value: float,
        tags: dict[str, str] | None,
        metric_type: str,
        unit: str | None = None,
    ):
        """Record a metric in memory and optionally in database."""
        metric = Metric(
            name=name,
            value=value,
            timestamp=datetime.utcnow(),
            tags=tags or {},
            unit=unit,
        )

        # Store in memory
        self.metrics[name].append(metric)

        # Store in database if available
        if self.db_manager:
            try:
                self.db_manager.record_metric(name, value, unit, tags)
            except Exception as e:
                logger.error(f"Failed to record metric in database: {e}")

    # Metric retrieval methods

    def get_counter(self, name: str) -> float:
        """Get current counter value."""
        return self.counters.get(name, 0.0)

    def get_gauge(self, name: str) -> float:
        """Get current gauge value."""
        return self.gauges.get(name, 0.0)

    def get_histogram_stats(self, name: str) -> dict[str, float]:
        """Get histogram statistics."""
        values = self.histograms.get(name, [])
        if not values:
            return {
                "count": 0,
                "min": 0,
                "max": 0,
                "mean": 0,
                "p50": 0,
                "p95": 0,
                "p99": 0,
            }

        sorted_values = sorted(values)
        count = len(values)

        return {
            "count": count,
            "min": min(values),
            "max": max(values),
            "mean": sum(values) / count,
            "p50": sorted_values[int(count * 0.5)],
            "p95": sorted_values[int(count * 0.95)],
            "p99": sorted_values[int(count * 0.99)],
        }

    def get_metrics_summary(self) -> dict[str, Any]:
        """Get summary of all metrics."""
        return {
            "counters": dict(self.counters),
            "gauges": dict(self.gauges),
            "histograms": {
                name: self.get_histogram_stats(name) for name in self.histograms.keys()
            },
            "total_metrics": len(self.metrics),
            "collection_running": self.running,
        }

    def get_metric_history(self, name: str, limit: int = 100) -> list[Metric]:
        """Get recent history for a specific metric."""
        return list(self.metrics.get(name, []))[-limit:]

    # Context managers for timing

    class Timer:
        """Context manager for timing operations."""

        def __init__(
            self,
            collector: "MetricsCollector",
            name: str,
            tags: dict[str, str] | None = None,
        ):
            self.collector = collector
            self.name = name
            self.tags = tags
            self.start_time = None

        def __enter__(self):
            self.start_time = time.time()
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            if self.start_time:
                duration_ms = (time.time() - self.start_time) * 1000
                self.collector.record_timing(self.name, duration_ms, self.tags)

    def timer(self, name: str, tags: dict[str, str] | None = None) -> Timer:
        """Create a timer context manager."""
        return self.Timer(self, name, tags)

    # Cleanup methods

    async def cleanup_old_metrics(self):
        """Clean up old metrics from database."""
        if self.db_manager:
            try:
                self.db_manager.cleanup_old_data(self.retention_days)
                logger.info(f"Cleaned up metrics older than {self.retention_days} days")
            except Exception as e:
                logger.error(f"Failed to cleanup old metrics: {e}")

    def reset_metrics(self):
        """Reset all in-memory metrics."""
        self.metrics.clear()
        self.counters.clear()
        self.gauges.clear()
        self.histograms.clear()
        logger.info("Reset all metrics")
