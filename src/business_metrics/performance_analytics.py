"""
Performance analytics for the Kindle Sync application.

Tracks system performance and optimization metrics.
"""

import time
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from loguru import logger


@dataclass
class PerformanceMetric:
    """Represents a performance metric measurement."""

    metric_name: str
    value: float
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None


class PerformanceAnalytics:
    """Collects and analyzes system performance data."""

    def __init__(self, max_measurements: int = 10000):
        """
        Initialize performance analytics.

        Args:
            max_measurements: Maximum number of measurements to keep in memory
        """
        self.max_measurements = max_measurements
        self.measurements: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=max_measurements)
        )
        self.performance_events: List[PerformanceMetric] = []

        # Performance thresholds
        self.thresholds = {
            "file_processing_time": 30.0,  # seconds
            "memory_usage": 80.0,  # percentage
            "cpu_usage": 80.0,  # percentage
            "disk_usage": 90.0,  # percentage
            "response_time": 5.0,  # seconds
        }

        logger.info("Performance analytics initialized")

    def record_metric(
        self, metric_name: str, value: float, metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Record a performance metric.

        Args:
            metric_name: Name of the metric
            value: Metric value
            metadata: Additional metric metadata
        """
        measurement = PerformanceMetric(
            metric_name=metric_name,
            value=value,
            timestamp=datetime.utcnow(),
            metadata=metadata,
        )

        self.measurements[metric_name].append(measurement)
        self.performance_events.append(measurement)

        # Check if metric exceeds threshold
        threshold = self.thresholds.get(metric_name)
        if threshold and value > threshold:
            logger.warning(
                f"Performance threshold exceeded: {metric_name} = {value} (threshold: {threshold})"
            )

        logger.debug(f"Recorded metric: {metric_name} = {value}")

    def get_metric_summary(self, metric_name: str, hours: int = 24) -> Dict[str, Any]:
        """
        Get summary statistics for a specific metric.

        Args:
            metric_name: Name of the metric
            hours: Number of hours to analyze

        Returns:
            Metric summary statistics
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

        # Filter recent measurements
        recent_measurements = [
            m for m in self.measurements[metric_name] if m.timestamp >= cutoff_time
        ]

        if not recent_measurements:
            return {
                "metric_name": metric_name,
                "count": 0,
                "average": 0.0,
                "min": 0.0,
                "max": 0.0,
                "median": 0.0,
                "p95": 0.0,
                "p99": 0.0,
                "threshold_exceeded": 0,
            }

        values = [m.value for m in recent_measurements]
        sorted_values = sorted(values)
        n = len(sorted_values)

        # Calculate statistics
        average = sum(values) / n
        min_value = min(values)
        max_value = max(values)
        median = sorted_values[n // 2] if n > 0 else 0
        p95 = sorted_values[int(n * 0.95)] if n > 0 else 0
        p99 = sorted_values[int(n * 0.99)] if n > 0 else 0

        # Count threshold violations
        threshold = self.thresholds.get(metric_name)
        threshold_exceeded = (
            sum(1 for v in values if threshold and v > threshold) if threshold else 0
        )

        return {
            "metric_name": metric_name,
            "count": n,
            "average": round(average, 2),
            "min": round(min_value, 2),
            "max": round(max_value, 2),
            "median": round(median, 2),
            "p95": round(p95, 2),
            "p99": round(p99, 2),
            "threshold_exceeded": threshold_exceeded,
            "threshold": threshold,
        }

    def get_performance_trends(
        self, metric_name: str, hours: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Get performance trends for a specific metric.

        Args:
            metric_name: Name of the metric
            hours: Number of hours to analyze

        Returns:
            List of trend data points
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

        # Filter recent measurements
        recent_measurements = [
            m for m in self.measurements[metric_name] if m.timestamp >= cutoff_time
        ]

        # Group by hour
        hourly_data = defaultdict(list)
        for measurement in recent_measurements:
            hour_key = measurement.timestamp.replace(minute=0, second=0, microsecond=0)
            hourly_data[hour_key].append(measurement.value)

        # Calculate hourly statistics
        trend_data = []
        for hour, values in sorted(hourly_data.items()):
            if values:
                trend_data.append(
                    {
                        "timestamp": hour.isoformat(),
                        "count": len(values),
                        "average": round(sum(values) / len(values), 2),
                        "min": round(min(values), 2),
                        "max": round(max(values), 2),
                        "median": round(sorted(values)[len(values) // 2], 2),
                    }
                )

        return trend_data

    def get_system_health_score(self, hours: int = 24) -> Dict[str, Any]:
        """
        Calculate overall system health score.

        Args:
            hours: Number of hours to analyze

        Returns:
            System health score and breakdown
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

        health_scores = {}
        overall_score = 100.0

        for metric_name, threshold in self.thresholds.items():
            # Get recent measurements
            recent_measurements = [
                m for m in self.measurements[metric_name] if m.timestamp >= cutoff_time
            ]

            if not recent_measurements:
                health_scores[metric_name] = 100.0
                continue

            values = [m.value for m in recent_measurements]
            average_value = sum(values) / len(values)

            # Calculate health score (100 - percentage of threshold used)
            if threshold > 0:
                threshold_usage = (average_value / threshold) * 100
                health_score = max(0, 100 - threshold_usage)
            else:
                health_score = 100.0

            health_scores[metric_name] = round(health_score, 2)
            overall_score = min(overall_score, health_score)

        # Determine health status
        if overall_score >= 90:
            status = "excellent"
        elif overall_score >= 75:
            status = "good"
        elif overall_score >= 50:
            status = "fair"
        else:
            status = "poor"

        return {
            "overall_score": round(overall_score, 2),
            "status": status,
            "metric_scores": health_scores,
            "analysis_period_hours": hours,
        }

    def get_performance_alerts(self, hours: int = 1) -> List[Dict[str, Any]]:
        """
        Get performance alerts for metrics exceeding thresholds.

        Args:
            hours: Number of hours to check for alerts

        Returns:
            List of performance alerts
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        alerts = []

        for metric_name, threshold in self.thresholds.items():
            # Get recent measurements
            recent_measurements = [
                m for m in self.measurements[metric_name] if m.timestamp >= cutoff_time
            ]

            if not recent_measurements:
                continue

            # Check for threshold violations
            violations = [m for m in recent_measurements if m.value > threshold]

            if violations:
                # Calculate violation statistics
                violation_values = [v.value for v in violations]
                max_violation = max(violation_values)
                avg_violation = sum(violation_values) / len(violation_values)

                alerts.append(
                    {
                        "metric_name": metric_name,
                        "threshold": threshold,
                        "violations_count": len(violations),
                        "max_violation": round(max_violation, 2),
                        "avg_violation": round(avg_violation, 2),
                        "severity": "high"
                        if max_violation > threshold * 1.5
                        else "medium",
                        "first_violation": min(
                            violations, key=lambda x: x.timestamp
                        ).timestamp.isoformat(),
                        "last_violation": max(
                            violations, key=lambda x: x.timestamp
                        ).timestamp.isoformat(),
                    }
                )

        return alerts

    def get_optimization_recommendations(self) -> List[Dict[str, Any]]:
        """
        Generate performance optimization recommendations.

        Returns:
            List of optimization recommendations
        """
        recommendations = []

        # Analyze each metric for optimization opportunities
        for metric_name, threshold in self.thresholds.items():
            recent_measurements = list(self.measurements[metric_name])[
                -100:
            ]  # Last 100 measurements

            if not recent_measurements:
                continue

            values = [m.value for m in recent_measurements]
            average_value = sum(values) / len(values)
            max_value = max(values)

            # Generate recommendations based on performance patterns
            if average_value > threshold * 0.8:  # Approaching threshold
                recommendations.append(
                    {
                        "metric": metric_name,
                        "issue": f"High average {metric_name}",
                        "current_value": round(average_value, 2),
                        "threshold": threshold,
                        "recommendation": self._get_optimization_recommendation(
                            metric_name
                        ),
                        "priority": "high" if average_value > threshold else "medium",
                    }
                )

            if max_value > threshold * 1.2:  # Occasional spikes
                recommendations.append(
                    {
                        "metric": metric_name,
                        "issue": f"Occasional spikes in {metric_name}",
                        "current_value": round(max_value, 2),
                        "threshold": threshold,
                        "recommendation": self._get_spike_optimization_recommendation(
                            metric_name
                        ),
                        "priority": "medium",
                    }
                )

        return recommendations

    def _get_optimization_recommendation(self, metric_name: str) -> str:
        """Get optimization recommendation for a metric."""
        recommendations = {
            "file_processing_time": "Consider optimizing file processing algorithms or increasing processing resources",
            "memory_usage": "Review memory usage patterns and consider memory optimization or increasing available memory",
            "cpu_usage": "Optimize CPU-intensive operations or consider scaling to more powerful hardware",
            "disk_usage": "Clean up temporary files and consider increasing disk space",
            "response_time": "Optimize network operations and consider caching frequently accessed data",
        }

        return recommendations.get(metric_name, "Review and optimize this metric")

    def _get_spike_optimization_recommendation(self, metric_name: str) -> str:
        """Get optimization recommendation for metric spikes."""
        recommendations = {
            "file_processing_time": "Implement request queuing and rate limiting to prevent processing spikes",
            "memory_usage": "Implement memory monitoring and automatic cleanup to prevent memory spikes",
            "cpu_usage": "Implement CPU throttling and load balancing to distribute processing load",
            "disk_usage": "Implement automatic cleanup and monitoring to prevent disk space spikes",
            "response_time": "Implement caching and connection pooling to reduce response time spikes",
        }

        return recommendations.get(
            metric_name, "Implement monitoring and throttling for this metric"
        )

    def cleanup_old_data(self, days: int = 30):
        """
        Clean up old performance data.

        Args:
            days: Keep data for this many days
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Clean up performance events
        self.performance_events = [
            event for event in self.performance_events if event.timestamp >= cutoff_date
        ]

        # Clean up measurements (deques automatically handle maxlen)
        for metric_name in list(self.measurements.keys()):
            # Remove old measurements
            while (
                self.measurements[metric_name]
                and self.measurements[metric_name][0].timestamp < cutoff_date
            ):
                self.measurements[metric_name].popleft()

        logger.info(f"Cleaned up performance data older than {days} days")
