"""
Distributed tracing implementation using OpenTelemetry.

Provides tracing capabilities for monitoring request flows across the application.
"""

import os
from contextlib import contextmanager
from typing import Any, Dict, Optional

from loguru import logger
from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.aiohttp_client import AioHttpClientInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


class TracingManager:
    """Manages distributed tracing configuration and instrumentation."""

    def __init__(
        self, service_name: str = "kindle-sync", config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize tracing manager.

        Args:
            service_name: Name of the service for tracing
            config: Tracing configuration dictionary
        """
        self.service_name = service_name
        self.config = config or {}
        self.tracer_provider: Optional[TracerProvider] = None
        self.tracer = None
        self._instrumentors = []

    def setup_tracing(self) -> bool:
        """
        Set up distributed tracing with OpenTelemetry.

        Returns:
            True if tracing was set up successfully, False otherwise
        """
        try:
            # Create resource with service information
            resource = Resource.create(
                {
                    "service.name": self.service_name,
                    "service.version": self.config.get("version", "1.0.0"),
                    "deployment.environment": self.config.get(
                        "environment", "development"
                    ),
                }
            )

            # Create tracer provider
            self.tracer_provider = TracerProvider(resource=resource)
            trace.set_tracer_provider(self.tracer_provider)

            # Set up exporters based on configuration
            self._setup_exporters()

            # Get tracer instance
            self.tracer = trace.get_tracer(__name__)

            # Set up instrumentation
            self._setup_instrumentation()

            logger.info(
                f"Distributed tracing initialized for service: {self.service_name}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to initialize distributed tracing: {e}")
            return False

    def _setup_exporters(self):
        """Set up trace exporters based on configuration."""
        exporters = self.config.get("exporters", {})

        # Jaeger exporter
        if exporters.get("jaeger", {}).get("enabled", False):
            jaeger_config = exporters["jaeger"]
            jaeger_exporter = JaegerExporter(
                agent_host_name=jaeger_config.get("host", "localhost"),
                agent_port=jaeger_config.get("port", 14268),
                collector_endpoint=jaeger_config.get("collector_endpoint"),
            )

            span_processor = BatchSpanProcessor(jaeger_exporter)
            self.tracer_provider.add_span_processor(span_processor)
            logger.info("Jaeger exporter configured")

        # OTLP exporter (for Jaeger, Zipkin, etc.)
        if exporters.get("otlp", {}).get("enabled", False):
            otlp_config = exporters["otlp"]
            otlp_exporter = OTLPSpanExporter(
                endpoint=otlp_config.get("endpoint", "http://localhost:4317"),
                headers=otlp_config.get("headers", {}),
            )

            span_processor = BatchSpanProcessor(otlp_exporter)
            self.tracer_provider.add_span_processor(span_processor)
            logger.info("OTLP exporter configured")

    def _setup_instrumentation(self):
        """Set up automatic instrumentation for common libraries."""
        instrumentation_config = self.config.get("instrumentation", {})

        # HTTP client instrumentation
        if instrumentation_config.get("aiohttp", True):
            try:
                aiohttp_instrumentor = AioHttpClientInstrumentor()
                aiohttp_instrumentor.instrument()
                self._instrumentors.append(aiohttp_instrumentor)
                logger.info("AioHTTP client instrumentation enabled")
            except Exception as e:
                logger.warning(f"Failed to instrument AioHTTP: {e}")

        # SQLAlchemy instrumentation
        if instrumentation_config.get("sqlalchemy", True):
            try:
                sqlalchemy_instrumentor = SQLAlchemyInstrumentor()
                sqlalchemy_instrumentor.instrument()
                self._instrumentors.append(sqlalchemy_instrumentor)
                logger.info("SQLAlchemy instrumentation enabled")
            except Exception as e:
                logger.warning(f"Failed to instrument SQLAlchemy: {e}")

        # Requests instrumentation
        if instrumentation_config.get("requests", True):
            try:
                requests_instrumentor = RequestsInstrumentor()
                requests_instrumentor.instrument()
                self._instrumentors.append(requests_instrumentor)
                logger.info("Requests instrumentation enabled")
            except Exception as e:
                logger.warning(f"Failed to instrument Requests: {e}")

    def shutdown(self):
        """Shutdown tracing and clean up resources."""
        try:
            # Uninstrument all instrumentors
            for instrumentor in self._instrumentors:
                try:
                    instrumentor.uninstrument()
                except Exception as e:
                    logger.warning(f"Failed to uninstrument: {e}")

            # Shutdown tracer provider
            if self.tracer_provider:
                self.tracer_provider.shutdown()

            logger.info("Distributed tracing shutdown completed")

        except Exception as e:
            logger.error(f"Error during tracing shutdown: {e}")

    @contextmanager
    def trace_span(self, name: str, attributes: Optional[Dict[str, Any]] = None):
        """
        Context manager for creating a trace span.

        Args:
            name: Name of the span
            attributes: Optional attributes to add to the span

        Yields:
            Span object
        """
        if not self.tracer:
            yield None
            return

        with self.tracer.start_as_current_span(name) as span:
            if attributes and span:
                for key, value in attributes.items():
                    span.set_attribute(key, value)
            yield span

    def add_span_event(self, name: str, attributes: Optional[Dict[str, Any]] = None):
        """
        Add an event to the current span.

        Args:
            name: Name of the event
            attributes: Optional attributes for the event
        """
        current_span = trace.get_current_span()
        if current_span and current_span.is_recording():
            current_span.add_event(name, attributes or {})

    def set_span_attribute(self, key: str, value: Any):
        """
        Set an attribute on the current span.

        Args:
            key: Attribute key
            value: Attribute value
        """
        current_span = trace.get_current_span()
        if current_span and current_span.is_recording():
            current_span.set_attribute(key, value)

    def set_span_status(self, status_code: str, description: Optional[str] = None):
        """
        Set the status of the current span.

        Args:
            status_code: Status code (OK, ERROR, etc.)
            description: Optional status description
        """
        current_span = trace.get_current_span()
        if current_span and current_span.is_recording():
            from opentelemetry.trace import Status, StatusCode

            status = Status(
                StatusCode.ERROR if status_code == "ERROR" else StatusCode.OK,
                description,
            )
            current_span.set_status(status)


# Global tracing manager instance
_tracing_manager: Optional[TracingManager] = None


def initialize_tracing(
    service_name: str = "kindle-sync", config: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Initialize global tracing manager.

    Args:
        service_name: Name of the service
        config: Tracing configuration

    Returns:
        True if initialization was successful
    """
    global _tracing_manager

    if _tracing_manager is None:
        _tracing_manager = TracingManager(service_name, config)
        return _tracing_manager.setup_tracing()

    return True


def get_tracer():
    """
    Get the global tracer instance.

    Returns:
        Tracer instance or None if not initialized
    """
    global _tracing_manager
    return _tracing_manager.tracer if _tracing_manager else None


def get_tracing_manager() -> Optional[TracingManager]:
    """
    Get the global tracing manager instance.

    Returns:
        TracingManager instance or None if not initialized
    """
    global _tracing_manager
    return _tracing_manager


def shutdown_tracing():
    """Shutdown global tracing manager."""
    global _tracing_manager

    if _tracing_manager:
        _tracing_manager.shutdown()
        _tracing_manager = None
