"""Monitoring and health check package."""

from .health_checks import HealthChecker, HealthStatus
from .metrics import MetricsCollector

try:
    from .prometheus_exporter import PrometheusExporter
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PrometheusExporter = None
    PROMETHEUS_AVAILABLE = False

__all__ = [
    "HealthChecker",
    "HealthStatus", 
    "MetricsCollector",
]

if PROMETHEUS_AVAILABLE:
    __all__.append("PrometheusExporter")
