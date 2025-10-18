"""Database manager for handling connections and operations."""

import json
from typing import Optional, List, Dict, Any
from pathlib import Path
from datetime import datetime, timedelta
from contextlib import contextmanager
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
from loguru import logger

from .models import Base, ProcessedFile, FileOperation, SystemMetrics, HealthCheck, ProcessingQueue, ProcessingStatus
from ..core.exceptions import ConfigurationError, ErrorSeverity


class DatabaseManager:
    """Manages database connections and provides high-level operations."""
    
    def __init__(self, database_url: str, echo: bool = False):
        """
        Initialize database manager.
        
        Args:
            database_url: SQLAlchemy database URL
            echo: Whether to echo SQL statements (for debugging)
        """
        self.database_url = database_url
        self.engine = create_engine(
            database_url,
            echo=echo,
            pool_pre_ping=True,  # Verify connections before use
            pool_recycle=3600,   # Recycle connections after 1 hour
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        logger.info(f"Database manager initialized with URL: {database_url}")
    
    def create_tables(self):
        """Create all database tables."""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created successfully")
        except SQLAlchemyError as e:
            logger.error(f"Failed to create database tables: {e}")
            raise ConfigurationError(
                f"Database initialization failed: {e}",
                config_key="database",
                severity=ErrorSeverity.CRITICAL
            )
    
    def drop_tables(self):
        """Drop all database tables (use with caution!)."""
        try:
            Base.metadata.drop_all(bind=self.engine)
            logger.warning("All database tables dropped")
        except SQLAlchemyError as e:
            logger.error(f"Failed to drop database tables: {e}")
            raise
    
    @contextmanager
    def get_session(self):
        """Get a database session with automatic cleanup."""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    # File tracking operations
    
    def record_file_processing(
        self,
        file_path: str,
        file_hash: str,
        file_size: int,
        file_type: str,
        status: ProcessingStatus,
        processing_time_ms: Optional[int] = None,
        error_message: Optional[str] = None,
        retry_count: int = 0
    ) -> int:
        """Record a file processing attempt."""
        with self.get_session() as session:
            # Check if file already exists
            existing = session.query(ProcessedFile).filter_by(file_path=file_path).first()
            
            if existing:
                # Update existing record
                existing.file_hash = file_hash
                existing.file_size = file_size
                existing.status = status
                existing.processing_time_ms = processing_time_ms
                existing.error_message = error_message
                existing.retry_count = retry_count
                existing.processed_at = datetime.utcnow()
                file_id = existing.id
            else:
                # Create new record
                processed_file = ProcessedFile(
                    file_path=file_path,
                    file_hash=file_hash,
                    file_size=file_size,
                    file_type=file_type,
                    status=status,
                    processing_time_ms=processing_time_ms,
                    error_message=error_message,
                    retry_count=retry_count
                )
                session.add(processed_file)
                session.flush()  # Get the ID
                file_id = processed_file.id
            
            return file_id
    
    def record_file_operation(
        self,
        file_id: int,
        operation_type: str,
        status: ProcessingStatus,
        processing_time_ms: Optional[int] = None,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """Record an individual file operation."""
        with self.get_session() as session:
            operation = FileOperation(
                file_id=file_id,
                operation_type=operation_type,
                status=status,
                processing_time_ms=processing_time_ms,
                error_message=error_message,
                metadata=json.dumps(metadata) if metadata else None
            )
            session.add(operation)
            session.flush()
            return operation.id
    
    def get_file_processing_history(self, file_path: str) -> Optional[ProcessedFile]:
        """Get processing history for a specific file."""
        with self.get_session() as session:
            return session.query(ProcessedFile).filter_by(file_path=file_path).first()
    
    def get_recent_files(self, limit: int = 100, status: Optional[ProcessingStatus] = None) -> List[ProcessedFile]:
        """Get recently processed files."""
        with self.get_session() as session:
            query = session.query(ProcessedFile).order_by(ProcessedFile.processed_at.desc())
            
            if status:
                query = query.filter_by(status=status)
            
            return query.limit(limit).all()
    
    def get_files_by_status(self, status: ProcessingStatus) -> List[ProcessedFile]:
        """Get all files with a specific status."""
        with self.get_session() as session:
            return session.query(ProcessedFile).filter_by(status=status).all()
    
    # Queue management operations
    
    def add_to_queue(
        self,
        file_path: str,
        file_hash: str,
        priority: int = 0,
        scheduled_for: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """Add a file to the processing queue."""
        with self.get_session() as session:
            # Check if already in queue
            existing = session.query(ProcessingQueue).filter_by(file_path=file_path).first()
            
            if existing:
                # Update existing entry
                existing.priority = priority
                existing.scheduled_for = scheduled_for
                existing.metadata = json.dumps(metadata) if metadata else None
                existing.queued_at = datetime.utcnow()
                return existing.id
            else:
                # Create new entry
                queue_item = ProcessingQueue(
                    file_path=file_path,
                    file_hash=file_hash,
                    priority=priority,
                    scheduled_for=scheduled_for,
                    metadata=json.dumps(metadata) if metadata else None
                )
                session.add(queue_item)
                session.flush()
                return queue_item.id
    
    def get_next_queue_item(self) -> Optional[ProcessingQueue]:
        """Get the next item from the processing queue."""
        with self.get_session() as session:
            now = datetime.utcnow()
            return session.query(ProcessingQueue).filter(
                ProcessingQueue.scheduled_for <= now
            ).order_by(
                ProcessingQueue.priority.desc(),
                ProcessingQueue.queued_at.asc()
            ).first()
    
    def remove_from_queue(self, file_path: str):
        """Remove a file from the processing queue."""
        with self.get_session() as session:
            session.query(ProcessingQueue).filter_by(file_path=file_path).delete()
    
    def get_queue_size(self) -> int:
        """Get the current queue size."""
        with self.get_session() as session:
            return session.query(ProcessingQueue).count()
    
    # Metrics operations
    
    def record_metric(
        self,
        metric_name: str,
        metric_value: float,
        metric_unit: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None
    ):
        """Record a system metric."""
        with self.get_session() as session:
            metric = SystemMetrics(
                metric_name=metric_name,
                metric_value=metric_value,
                metric_unit=metric_unit,
                tags=json.dumps(tags) if tags else None
            )
            session.add(metric)
    
    def get_metrics(
        self,
        metric_name: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[SystemMetrics]:
        """Get metrics for a specific metric name."""
        with self.get_session() as session:
            query = session.query(SystemMetrics).filter_by(metric_name=metric_name)
            
            if start_time:
                query = query.filter(SystemMetrics.timestamp >= start_time)
            if end_time:
                query = query.filter(SystemMetrics.timestamp <= end_time)
            
            return query.order_by(SystemMetrics.timestamp.desc()).limit(limit).all()
    
    def get_latest_metric(self, metric_name: str) -> Optional[SystemMetrics]:
        """Get the latest metric value for a specific metric name."""
        with self.get_session() as session:
            return session.query(SystemMetrics).filter_by(
                metric_name=metric_name
            ).order_by(SystemMetrics.timestamp.desc()).first()
    
    # Health check operations
    
    def record_health_check(
        self,
        check_name: str,
        status: str,
        response_time_ms: Optional[int] = None,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Record a health check result."""
        with self.get_session() as session:
            health_check = HealthCheck(
                check_name=check_name,
                status=status,
                response_time_ms=response_time_ms,
                error_message=error_message,
                metadata=json.dumps(metadata) if metadata else None
            )
            session.add(health_check)
    
    def get_health_check_history(
        self,
        check_name: str,
        limit: int = 100
    ) -> List[HealthCheck]:
        """Get health check history for a specific check."""
        with self.get_session() as session:
            return session.query(HealthCheck).filter_by(
                check_name=check_name
            ).order_by(HealthCheck.timestamp.desc()).limit(limit).all()
    
    def get_latest_health_check(self, check_name: str) -> Optional[HealthCheck]:
        """Get the latest health check result for a specific check."""
        with self.get_session() as session:
            return session.query(HealthCheck).filter_by(
                check_name=check_name
            ).order_by(HealthCheck.timestamp.desc()).first()
    
    # Statistics and reporting
    
    def get_processing_statistics(self, days: int = 7) -> Dict[str, Any]:
        """Get processing statistics for the last N days."""
        with self.get_session() as session:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # Total files processed
            total_files = session.query(ProcessedFile).filter(
                ProcessedFile.processed_at >= start_date
            ).count()
            
            # Files by status
            status_counts = {}
            for status in ProcessingStatus:
                count = session.query(ProcessedFile).filter(
                    ProcessedFile.processed_at >= start_date,
                    ProcessedFile.status == status
                ).count()
                status_counts[status.value] = count
            
            # Average processing time
            avg_time_result = session.query(
                text("AVG(processing_time_ms)")
            ).filter(
                ProcessedFile.processed_at >= start_date,
                ProcessedFile.processing_time_ms.isnot(None)
            ).scalar()
            
            avg_processing_time = float(avg_time_result) if avg_time_result else 0.0
            
            return {
                "total_files": total_files,
                "status_counts": status_counts,
                "average_processing_time_ms": avg_processing_time,
                "period_days": days
            }
    
    def cleanup_old_data(self, days: int = 30):
        """Clean up old data to prevent database bloat."""
        with self.get_session() as session:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Clean up old metrics
            metrics_deleted = session.query(SystemMetrics).filter(
                SystemMetrics.timestamp < cutoff_date
            ).delete()
            
            # Clean up old health checks
            health_checks_deleted = session.query(HealthCheck).filter(
                HealthCheck.timestamp < cutoff_date
            ).delete()
            
            logger.info(f"Cleaned up {metrics_deleted} old metrics and {health_checks_deleted} old health checks")
    
    def get_database_info(self) -> Dict[str, Any]:
        """Get database information and statistics."""
        with self.get_session() as session:
            # Table sizes
            table_counts = {}
            for table in [ProcessedFile, FileOperation, SystemMetrics, HealthCheck, ProcessingQueue]:
                count = session.query(table).count()
                table_counts[table.__tablename__] = count
            
            # Database size (SQLite specific)
            if "sqlite" in self.database_url:
                size_result = session.query(text("page_count * page_size as size")).from_statement(
                    text("PRAGMA page_count, page_size")
                ).scalar()
                db_size_mb = (size_result / (1024 * 1024)) if size_result else 0
            else:
                db_size_mb = None
            
            return {
                "table_counts": table_counts,
                "database_size_mb": db_size_mb,
                "database_url": self.database_url
            }
