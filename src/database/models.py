"""Database models for persistent state management."""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class ProcessingStatus(str, Enum):
    """Processing status enumeration."""

    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class ProcessedFile(Base):  # type: ignore
    """Model for tracking processed files."""

    __tablename__ = "processed_files"

    id = Column(Integer, primary_key=True)
    file_path = Column(String(500), unique=True, nullable=False, index=True)
    file_hash = Column(String(64), nullable=False, index=True)  # SHA-256
    file_size = Column(Integer, nullable=False)
    file_type = Column(String(10), nullable=False)  # .md, .pdf
    processed_at = Column(DateTime, default=datetime.utcnow, index=True)
    status = Column(String(20), nullable=False, default=ProcessingStatus.PENDING)
    error_message = Column(Text, nullable=True)
    processing_time_ms = Column(Integer, nullable=True)
    retry_count = Column(Integer, default=0)

    # Relationships
    operations = relationship(
        "FileOperation", back_populates="file", cascade="all, delete-orphan"
    )

    # Indexes for performance
    __table_args__ = (
        Index("idx_file_path_status", "file_path", "status"),
        Index("idx_processed_at_status", "processed_at", "status"),
    )


class FileOperation(Base):  # type: ignore
    """Model for tracking individual operations on files."""

    __tablename__ = "file_operations"

    id = Column(Integer, primary_key=True)
    file_id = Column(Integer, ForeignKey("processed_files.id"), nullable=False)
    operation_type = Column(String(50), nullable=False)  # convert, send, backup, etc.
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    status = Column(String(20), nullable=False, default=ProcessingStatus.PENDING)
    error_message = Column(Text, nullable=True)
    processing_time_ms = Column(Integer, nullable=True)
    operation_metadata = Column(Text, nullable=True)  # JSON string for additional data

    # Relationships
    file = relationship("ProcessedFile", back_populates="operations")

    # Indexes
    __table_args__ = (
        Index("idx_file_id_operation", "file_id", "operation_type"),
        Index("idx_started_at_status", "started_at", "status"),
    )


class SystemMetrics(Base):  # type: ignore
    """Model for storing system performance metrics."""

    __tablename__ = "system_metrics"

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    metric_name = Column(String(100), nullable=False, index=True)
    metric_value = Column(Float, nullable=False)
    metric_unit = Column(String(20), nullable=True)  # ms, bytes, count, etc.
    tags = Column(Text, nullable=True)  # JSON string for tags

    # Indexes
    __table_args__ = (Index("idx_timestamp_metric", "timestamp", "metric_name"),)


class HealthCheck(Base):  # type: ignore
    """Model for storing health check results."""

    __tablename__ = "health_checks"

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    check_name = Column(String(100), nullable=False, index=True)
    status = Column(String(20), nullable=False)  # healthy, unhealthy, degraded
    response_time_ms = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    metadata = Column(Text, nullable=True)  # JSON string for additional data

    # Indexes
    __table_args__ = (
        Index("idx_timestamp_check", "timestamp", "check_name"),
        Index("idx_check_status", "check_name", "status"),
    )


class ProcessingQueue(Base):  # type: ignore
    """Model for managing processing queue."""

    __tablename__ = "processing_queue"

    id = Column(Integer, primary_key=True)
    file_path = Column(String(500), nullable=False, unique=True, index=True)
    file_hash = Column(String(64), nullable=False)
    priority = Column(Integer, default=0)  # Higher number = higher priority
    queued_at = Column(DateTime, default=datetime.utcnow, index=True)
    scheduled_for = Column(
        DateTime, nullable=True, index=True
    )  # For delayed processing
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    metadata = Column(Text, nullable=True)  # JSON string for processing options

    # Indexes
    __table_args__ = (
        Index("idx_priority_scheduled", "priority", "scheduled_for"),
        Index("idx_queued_at_priority", "queued_at", "priority"),
    )
