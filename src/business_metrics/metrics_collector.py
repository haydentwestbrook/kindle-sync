"""
Business metrics collector for the Kindle Sync application.

Tracks business-relevant metrics like user engagement, content processing, and system performance.
"""

import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from loguru import logger

from ..monitoring.metrics import MetricsCollector


@dataclass
class UserSession:
    """Represents a user session."""

    user_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    files_processed: int = 0
    emails_sent: int = 0
    errors_encountered: int = 0
    total_processing_time: float = 0.0


@dataclass
class ContentMetrics:
    """Metrics for content processing."""

    total_files: int = 0
    markdown_files: int = 0
    pdf_files: int = 0
    successful_conversions: int = 0
    failed_conversions: int = 0
    average_processing_time: float = 0.0
    total_processing_time: float = 0.0


@dataclass
class UserEngagement:
    """User engagement metrics."""

    active_users: int = 0
    daily_active_users: int = 0
    weekly_active_users: int = 0
    monthly_active_users: int = 0
    average_session_duration: float = 0.0
    files_per_user: float = 0.0


class BusinessMetricsCollector:
    """Collects and manages business metrics."""

    def __init__(self, metrics_collector: Optional[MetricsCollector] = None):
        """
        Initialize business metrics collector.

        Args:
            metrics_collector: System metrics collector for integration
        """
        self.metrics_collector = metrics_collector
        self.user_sessions: Dict[str, UserSession] = {}
        self.content_metrics = ContentMetrics()
        self.user_engagement = UserEngagement()

        # Time-series data
        self.daily_metrics: deque = deque(maxlen=365)  # Keep 1 year
        self.hourly_metrics: deque = deque(maxlen=168)  # Keep 1 week

        # User activity tracking
        self.user_activity: Dict[str, List[datetime]] = defaultdict(list)
        self.daily_users: set = set()
        self.weekly_users: set = set()
        self.monthly_users: set = set()

        # Content tracking
        self.file_types: Dict[str, int] = defaultdict(int)
        self.processing_times: List[float] = []

        logger.info("Business metrics collector initialized")

    def start_user_session(self, user_id: str) -> str:
        """
        Start tracking a user session.

        Args:
            user_id: Unique identifier for the user

        Returns:
            Session ID
        """
        session_id = f"{user_id}_{int(time.time())}"
        session = UserSession(user_id=user_id, start_time=datetime.utcnow())

        self.user_sessions[session_id] = session

        # Track user activity
        now = datetime.utcnow()
        self.user_activity[user_id].append(now)
        self.daily_users.add(user_id)
        self.weekly_users.add(user_id)
        self.monthly_users.add(user_id)

        # Update active users
        self.user_engagement.active_users = len(self.user_sessions)

        logger.debug(f"Started user session: {session_id}")
        return session_id

    def end_user_session(self, session_id: str):
        """
        End a user session.

        Args:
            session_id: Session ID to end
        """
        if session_id in self.user_sessions:
            session = self.user_sessions[session_id]
            session.end_time = datetime.utcnow()

            # Calculate session duration
            duration = (session.end_time - session.start_time).total_seconds()

            # Update engagement metrics
            self._update_session_metrics(session, duration)

            # Remove from active sessions
            del self.user_sessions[session_id]
            self.user_engagement.active_users = len(self.user_sessions)

            logger.debug(f"Ended user session: {session_id}, duration: {duration}s")

    def record_file_processing(
        self, user_id: str, file_type: str, processing_time: float, success: bool
    ):
        """
        Record file processing metrics.

        Args:
            user_id: User who processed the file
            file_type: Type of file processed
            processing_time: Time taken to process
            success: Whether processing was successful
        """
        # Update content metrics
        self.content_metrics.total_files += 1
        self.content_metrics.total_processing_time += processing_time
        self.processing_times.append(processing_time)

        # Keep only last 1000 processing times for average calculation
        if len(self.processing_times) > 1000:
            self.processing_times = self.processing_times[-1000:]

        self.content_metrics.average_processing_time = sum(self.processing_times) / len(
            self.processing_times
        )

        if file_type.lower() == "markdown":
            self.content_metrics.markdown_files += 1
        elif file_type.lower() == "pdf":
            self.content_metrics.pdf_files += 1

        if success:
            self.content_metrics.successful_conversions += 1
        else:
            self.content_metrics.failed_conversions += 1

        # Update file type statistics
        self.file_types[file_type] += 1

        # Update user session if active
        for session in self.user_sessions.values():
            if session.user_id == user_id:
                session.files_processed += 1
                session.total_processing_time += processing_time
                if not success:
                    session.errors_encountered += 1
                break

        # Record in system metrics if available
        if self.metrics_collector:
            self.metrics_collector.record_counter(
                "business_files_processed_total",
                1,
                {"file_type": file_type, "success": str(success).lower()},
            )
            self.metrics_collector.record_timing(
                "business_file_processing_duration",
                processing_time * 1000,
                {"file_type": file_type},
            )

    def record_email_sent(self, user_id: str, success: bool):
        """
        Record email sending metrics.

        Args:
            user_id: User who sent the email
            success: Whether email was sent successfully
        """
        # Update user session if active
        for session in self.user_sessions.values():
            if session.user_id == user_id:
                if success:
                    session.emails_sent += 1
                else:
                    session.errors_encountered += 1
                break

        # Record in system metrics if available
        if self.metrics_collector:
            self.metrics_collector.record_counter(
                "business_emails_sent_total", 1, {"success": str(success).lower()}
            )

    def _update_session_metrics(self, session: UserSession, duration: float):
        """Update session-based metrics."""
        # Update average session duration
        total_sessions = len(self.daily_metrics) if self.daily_metrics else 1
        current_avg = self.user_engagement.average_session_duration
        self.user_engagement.average_session_duration = (
            current_avg * (total_sessions - 1) + duration
        ) / total_sessions

        # Update files per user
        if session.files_processed > 0:
            current_avg_files = self.user_engagement.files_per_user
            self.user_engagement.files_per_user = (
                current_avg_files * (total_sessions - 1) + session.files_processed
            ) / total_sessions

    def update_daily_metrics(self):
        """Update daily metrics and clean up old data."""
        now = datetime.utcnow()

        # Calculate daily active users
        self.user_engagement.daily_active_users = len(self.daily_users)

        # Calculate weekly active users
        week_ago = now - timedelta(days=7)
        weekly_users = set()
        for user_id, timestamps in self.user_activity.items():
            if any(ts >= week_ago for ts in timestamps):
                weekly_users.add(user_id)
        self.user_engagement.weekly_active_users = len(weekly_users)

        # Calculate monthly active users
        month_ago = now - timedelta(days=30)
        monthly_users = set()
        for user_id, timestamps in self.user_activity.items():
            if any(ts >= month_ago for ts in timestamps):
                monthly_users.add(user_id)
        self.user_engagement.monthly_active_users = len(monthly_users)

        # Store daily metrics
        daily_metric = {
            "date": now.date(),
            "active_users": self.user_engagement.daily_active_users,
            "files_processed": self.content_metrics.total_files,
            "emails_sent": sum(
                session.emails_sent for session in self.user_sessions.values()
            ),
            "average_processing_time": self.content_metrics.average_processing_time,
            "success_rate": (
                self.content_metrics.successful_conversions
                / max(1, self.content_metrics.total_files)
                * 100
            ),
        }

        self.daily_metrics.append(daily_metric)

        # Clean up old user activity data (keep last 30 days)
        cutoff_date = now - timedelta(days=30)
        for user_id in list(self.user_activity.keys()):
            self.user_activity[user_id] = [
                ts for ts in self.user_activity[user_id] if ts >= cutoff_date
            ]
            if not self.user_activity[user_id]:
                del self.user_activity[user_id]

        # Reset daily users
        self.daily_users.clear()

        logger.debug("Updated daily business metrics")

    def get_business_summary(self) -> Dict[str, Any]:
        """
        Get a summary of business metrics.

        Returns:
            Dictionary containing business metrics summary
        """
        return {
            "user_engagement": {
                "active_users": self.user_engagement.active_users,
                "daily_active_users": self.user_engagement.daily_active_users,
                "weekly_active_users": self.user_engagement.weekly_active_users,
                "monthly_active_users": self.user_engagement.monthly_active_users,
                "average_session_duration": round(
                    self.user_engagement.average_session_duration, 2
                ),
                "files_per_user": round(self.user_engagement.files_per_user, 2),
            },
            "content_metrics": {
                "total_files": self.content_metrics.total_files,
                "markdown_files": self.content_metrics.markdown_files,
                "pdf_files": self.content_metrics.pdf_files,
                "successful_conversions": self.content_metrics.successful_conversions,
                "failed_conversions": self.content_metrics.failed_conversions,
                "success_rate": round(
                    self.content_metrics.successful_conversions
                    / max(1, self.content_metrics.total_files)
                    * 100,
                    2,
                ),
                "average_processing_time": round(
                    self.content_metrics.average_processing_time, 2
                ),
            },
            "file_types": dict(self.file_types),
            "recent_activity": {
                "active_sessions": len(self.user_sessions),
                "total_users_tracked": len(self.user_activity),
            },
        }

    def get_trend_data(self, days: int = 30) -> List[Dict[str, Any]]:
        """
        Get trend data for the specified number of days.

        Args:
            days: Number of days to include in trend data

        Returns:
            List of daily metrics
        """
        cutoff_date = datetime.utcnow().date() - timedelta(days=days)

        return [
            metric for metric in self.daily_metrics if metric["date"] >= cutoff_date
        ]


# Global business metrics collector instance
_business_metrics: Optional[BusinessMetricsCollector] = None


def initialize_business_metrics(
    metrics_collector: Optional[MetricsCollector] = None,
) -> BusinessMetricsCollector:
    """
    Initialize global business metrics collector.

    Args:
        metrics_collector: System metrics collector for integration

    Returns:
        Initialized business metrics collector
    """
    global _business_metrics
    _business_metrics = BusinessMetricsCollector(metrics_collector)
    return _business_metrics


def get_business_metrics() -> Optional[BusinessMetricsCollector]:
    """
    Get the global business metrics collector instance.

    Returns:
        Business metrics collector instance or None if not initialized
    """
    global _business_metrics
    return _business_metrics
