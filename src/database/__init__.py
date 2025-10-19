"""Database package for persistent state management."""

try:
    from .manager import DatabaseManager
    from .migrations import run_migrations
    from .models import Base, FileOperation, HealthCheck, ProcessedFile, SystemMetrics

    __all__ = [
        "Base",
        "ProcessedFile",
        "FileOperation",
        "SystemMetrics",
        "HealthCheck",
        "DatabaseManager",
        "run_migrations",
    ]
except ImportError:
    # SQLAlchemy not available
    Base = None
    ProcessedFile = None
    FileOperation = None
    SystemMetrics = None
    HealthCheck = None
    DatabaseManager = None
    run_migrations = None

    __all__ = []
