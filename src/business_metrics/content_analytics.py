"""
Content analytics for the Kindle Sync application.

Tracks content processing and conversion metrics.
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from loguru import logger


@dataclass
class ContentProcessingEvent:
    """Represents a content processing event."""

    file_path: str
    file_type: str
    processing_time: float
    success: bool
    timestamp: datetime
    user_id: str | None = None
    metadata: dict[str, Any] | None = None


class ContentAnalytics:
    """Collects and analyzes content processing data."""

    def __init__(self):
        """Initialize content analytics."""
        self.processing_events: list[ContentProcessingEvent] = []
        self.file_type_stats: dict[str, dict[str, Any]] = defaultdict(
            lambda: {
                "total_files": 0,
                "successful": 0,
                "failed": 0,
                "total_processing_time": 0.0,
                "average_processing_time": 0.0,
            }
        )

        logger.info("Content analytics initialized")

    def record_processing_event(
        self,
        file_path: str,
        file_type: str,
        processing_time: float,
        success: bool,
        user_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        """
        Record a content processing event.

        Args:
            file_path: Path to the processed file
            file_type: Type of file (markdown, pdf, etc.)
            processing_time: Time taken to process in seconds
            success: Whether processing was successful
            user_id: User who processed the file
            metadata: Additional processing metadata
        """
        event = ContentProcessingEvent(
            file_path=file_path,
            file_type=file_type,
            processing_time=processing_time,
            success=success,
            timestamp=datetime.utcnow(),
            user_id=user_id,
            metadata=metadata,
        )

        self.processing_events.append(event)

        # Update file type statistics
        stats = self.file_type_stats[file_type]
        stats["total_files"] += 1
        stats["total_processing_time"] += processing_time

        if success:
            stats["successful"] += 1
        else:
            stats["failed"] += 1

        # Update average processing time
        stats["average_processing_time"] = (
            stats["total_processing_time"] / stats["total_files"]
        )

        logger.debug(f"Recorded processing event: {file_path} ({file_type})")

    def get_file_type_metrics(self, file_type: str | None = None) -> dict[str, Any]:
        """
        Get metrics for a specific file type or all file types.

        Args:
            file_type: Specific file type to analyze (None for all)

        Returns:
            File type metrics
        """
        if file_type:
            if file_type not in self.file_type_stats:
                return {
                    "file_type": file_type,
                    "total_files": 0,
                    "successful": 0,
                    "failed": 0,
                    "success_rate": 0.0,
                    "average_processing_time": 0.0,
                    "total_processing_time": 0.0,
                }

            stats = self.file_type_stats[file_type]
            success_rate = (
                (stats["successful"] / stats["total_files"] * 100)
                if stats["total_files"] > 0
                else 0
            )

            return {
                "file_type": file_type,
                "total_files": stats["total_files"],
                "successful": stats["successful"],
                "failed": stats["failed"],
                "success_rate": round(success_rate, 2),
                "average_processing_time": round(stats["average_processing_time"], 2),
                "total_processing_time": round(stats["total_processing_time"], 2),
            }
        else:
            # Return metrics for all file types
            all_metrics = {}
            for ft, stats in self.file_type_stats.items():
                success_rate = (
                    (stats["successful"] / stats["total_files"] * 100)
                    if stats["total_files"] > 0
                    else 0
                )

                all_metrics[ft] = {
                    "total_files": stats["total_files"],
                    "successful": stats["successful"],
                    "failed": stats["failed"],
                    "success_rate": round(success_rate, 2),
                    "average_processing_time": round(
                        stats["average_processing_time"], 2
                    ),
                    "total_processing_time": round(stats["total_processing_time"], 2),
                }

            return all_metrics

    def get_processing_trends(self, days: int = 30) -> dict[str, list[dict[str, Any]]]:
        """
        Get processing trends over time.

        Args:
            days: Number of days to analyze

        Returns:
            Processing trends by file type
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Filter recent events
        recent_events = [
            event for event in self.processing_events if event.timestamp >= cutoff_date
        ]

        # Group by file type and date
        trends = defaultdict(
            lambda: defaultdict(
                lambda: {
                    "total_files": 0,
                    "successful": 0,
                    "failed": 0,
                    "total_processing_time": 0.0,
                }
            )
        )

        for event in recent_events:
            date_key = event.timestamp.date().isoformat()
            daily_stats = trends[event.file_type][date_key]

            daily_stats["total_files"] += 1
            daily_stats["total_processing_time"] += event.processing_time

            if event.success:
                daily_stats["successful"] += 1
            else:
                daily_stats["failed"] += 1

        # Convert to list format
        result = {}
        for file_type, daily_data in trends.items():
            trend_data = []
            for date, stats in sorted(daily_data.items()):
                success_rate = (
                    (stats["successful"] / stats["total_files"] * 100)
                    if stats["total_files"] > 0
                    else 0
                )
                avg_processing_time = (
                    stats["total_processing_time"] / stats["total_files"]
                    if stats["total_files"] > 0
                    else 0
                )

                trend_data.append(
                    {
                        "date": date,
                        "total_files": stats["total_files"],
                        "successful": stats["successful"],
                        "failed": stats["failed"],
                        "success_rate": round(success_rate, 2),
                        "average_processing_time": round(avg_processing_time, 2),
                    }
                )

            result[file_type] = trend_data

        return result

    def get_performance_metrics(self, days: int = 30) -> dict[str, Any]:
        """
        Get performance metrics for content processing.

        Args:
            days: Number of days to analyze

        Returns:
            Performance metrics
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Filter recent events
        recent_events = [
            event for event in self.processing_events if event.timestamp >= cutoff_date
        ]

        if not recent_events:
            return {
                "total_files_processed": 0,
                "success_rate": 0.0,
                "average_processing_time": 0.0,
                "fastest_processing_time": 0.0,
                "slowest_processing_time": 0.0,
                "processing_time_percentiles": {},
            }

        # Calculate metrics
        total_files = len(recent_events)
        successful_files = sum(1 for event in recent_events if event.success)
        success_rate = (successful_files / total_files * 100) if total_files > 0 else 0

        processing_times = [event.processing_time for event in recent_events]
        average_processing_time = sum(processing_times) / len(processing_times)
        fastest_processing_time = min(processing_times)
        slowest_processing_time = max(processing_times)

        # Calculate percentiles
        sorted_times = sorted(processing_times)
        n = len(sorted_times)
        percentiles = {
            "p50": sorted_times[int(n * 0.5)] if n > 0 else 0,
            "p90": sorted_times[int(n * 0.9)] if n > 0 else 0,
            "p95": sorted_times[int(n * 0.95)] if n > 0 else 0,
            "p99": sorted_times[int(n * 0.99)] if n > 0 else 0,
        }

        return {
            "total_files_processed": total_files,
            "success_rate": round(success_rate, 2),
            "average_processing_time": round(average_processing_time, 2),
            "fastest_processing_time": round(fastest_processing_time, 2),
            "slowest_processing_time": round(slowest_processing_time, 2),
            "processing_time_percentiles": {
                k: round(v, 2) for k, v in percentiles.items()
            },
        }

    def get_user_content_metrics(self, user_id: str, days: int = 30) -> dict[str, Any]:
        """
        Get content processing metrics for a specific user.

        Args:
            user_id: User identifier
            days: Number of days to analyze

        Returns:
            User content metrics
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Filter events for this user
        user_events = [
            event
            for event in self.processing_events
            if event.user_id == user_id and event.timestamp >= cutoff_date
        ]

        if not user_events:
            return {
                "user_id": user_id,
                "total_files_processed": 0,
                "success_rate": 0.0,
                "average_processing_time": 0.0,
                "file_types_processed": {},
                "processing_trend": [],
            }

        # Calculate metrics
        total_files = len(user_events)
        successful_files = sum(1 for event in user_events if event.success)
        success_rate = (successful_files / total_files * 100) if total_files > 0 else 0

        processing_times = [event.processing_time for event in user_events]
        average_processing_time = sum(processing_times) / len(processing_times)

        # File types processed
        file_types = defaultdict(int)
        for event in user_events:
            file_types[event.file_type] += 1

        # Processing trend (daily)
        daily_trend = defaultdict(lambda: {"total": 0, "successful": 0})
        for event in user_events:
            date_key = event.timestamp.date().isoformat()
            daily_trend[date_key]["total"] += 1
            if event.success:
                daily_trend[date_key]["successful"] += 1

        trend_data = [
            {
                "date": date,
                "total_files": stats["total"],
                "successful_files": stats["successful"],
                "success_rate": round(
                    (stats["successful"] / stats["total"] * 100)
                    if stats["total"] > 0
                    else 0,
                    2,
                ),
            }
            for date, stats in sorted(daily_trend.items())
        ]

        return {
            "user_id": user_id,
            "total_files_processed": total_files,
            "success_rate": round(success_rate, 2),
            "average_processing_time": round(average_processing_time, 2),
            "file_types_processed": dict(file_types),
            "processing_trend": trend_data,
        }

    def cleanup_old_data(self, days: int = 90):
        """
        Clean up old processing event data.

        Args:
            days: Keep data for this many days
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Remove old events
        self.processing_events = [
            event for event in self.processing_events if event.timestamp >= cutoff_date
        ]

        logger.info(f"Cleaned up processing event data older than {days} days")
