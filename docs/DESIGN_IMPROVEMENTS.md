# Kindle Sync Application - Design Improvements Document

## Executive Summary

This document outlines a comprehensive set of improvements to transform the Kindle Scribe ↔ Obsidian Sync System from a functional prototype into a production-ready, enterprise-grade application. The improvements focus on security, reliability, performance, maintainability, and operational excellence.

## Table of Contents

1. [Current State Analysis](#current-state-analysis)
2. [Improvement Categories](#improvement-categories)
3. [High Priority Improvements](#high-priority-improvements)
4. [Medium Priority Improvements](#medium-priority-improvements)
5. [Low Priority Improvements](#low-priority-improvements)
6. [Infrastructure & DevOps](#infrastructure--devops)
7. [Implementation Roadmap](#implementation-roadmap)
8. [Success Metrics](#success-metrics)
9. [Risk Assessment](#risk-assessment)
10. [Appendices](#appendices)

## Current State Analysis

### Strengths
- ✅ Well-documented deployment process
- ✅ Comprehensive Docker setup for Raspberry Pi
- ✅ Modular architecture with clear separation of concerns
- ✅ Good test coverage structure
- ✅ Configuration management system

### Areas for Improvement
- ❌ Security vulnerabilities (plain text passwords)
- ❌ Limited error handling and recovery mechanisms
- ❌ Synchronous processing limiting performance
- ❌ No persistent state management
- ❌ Basic monitoring and observability
- ❌ Inconsistent type safety

## Improvement Categories

### 🔴 High Priority (Security & Reliability)
- Secrets management
- Error handling & resilience
- Input validation & sanitization

### 🟡 Medium Priority (Architecture & Performance)
- Async/await implementation
- Database integration
- Health checks & monitoring

### 🟢 Low Priority (Code Quality & Maintainability)
- Type hints & documentation
- Configuration schema validation
- Plugin architecture

### 🔧 Infrastructure & DevOps
- Enhanced Docker configuration
- CI/CD pipeline improvements
- Monitoring & observability

## High Priority Improvements

### 1. Secrets Management

#### Current State
```yaml
# config.yaml (insecure)
kindle:
  smtp_password: "your-app-password"  # Plain text
```

#### Proposed Solution
```python
# src/security/secrets_manager.py
import os
import base64
from cryptography.fernet import Fernet
from typing import Optional
from pathlib import Path

class SecretsManager:
    """Secure secrets management with encryption at rest."""
    
    def __init__(self, key_path: Optional[Path] = None):
        self.key_path = key_path or Path.home() / ".kindle-sync" / "secrets.key"
        self._ensure_key_exists()
        self.cipher = Fernet(self._load_key())
    
    def _ensure_key_exists(self):
        """Generate encryption key if it doesn't exist."""
        if not self.key_path.exists():
            self.key_path.parent.mkdir(parents=True, exist_ok=True)
            key = Fernet.generate_key()
            self.key_path.write_bytes(key)
            self.key_path.chmod(0o600)  # Owner read/write only
    
    def _load_key(self) -> bytes:
        """Load encryption key from file."""
        return self.key_path.read_bytes()
    
    def encrypt_secret(self, secret: str) -> str:
        """Encrypt a secret value."""
        return self.cipher.encrypt(secret.encode()).decode()
    
    def decrypt_secret(self, encrypted_secret: str) -> str:
        """Decrypt a secret value."""
        return self.cipher.decrypt(encrypted_secret.encode()).decode()
    
    def get_secret(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get secret from environment or encrypted storage."""
        # Priority: Environment variable > Encrypted config > Default
        env_key = f"KINDLE_SYNC_{key.upper()}"
        if env_value := os.getenv(env_key):
            return env_value
        
        # Try to decrypt from config
        try:
            encrypted_value = self.config.get(f"secrets.{key}")
            if encrypted_value:
                return self.decrypt_secret(encrypted_value)
        except Exception:
            pass
        
        return default
```

#### Implementation Steps
1. Create `SecretsManager` class
2. Update `Config` class to use secrets manager
3. Migrate existing plain text secrets
4. Update documentation with new secret management process

#### Security Benefits
- 🔒 Encryption at rest for sensitive data
- 🔒 Environment variable support for containerized deployments
- 🔒 Secure key management with proper file permissions
- 🔒 Fallback mechanisms for different deployment scenarios

### 2. Error Handling & Resilience

#### Current State
```python
# Basic error handling
except Exception as e:
    logger.error(f"Error processing file {file_path}: {e}")
    self.stats["errors"] += 1
```

#### Proposed Solution
```python
# src/core/exceptions.py
from enum import Enum
from typing import Optional, Dict, Any
from dataclasses import dataclass

class ErrorSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class KindleSyncError(Exception):
    """Base exception for Kindle Sync application."""
    message: str
    severity: ErrorSeverity
    context: Optional[Dict[str, Any]] = None
    recoverable: bool = True
    retry_count: int = 0
    
    def __str__(self):
        return f"[{self.severity.value.upper()}] {self.message}"

class FileProcessingError(KindleSyncError):
    """Error during file processing."""
    pass

class EmailServiceError(KindleSyncError):
    """Error with email service."""
    pass

class ConfigurationError(KindleSyncError):
    """Configuration-related error."""
    pass

# src/core/retry.py
from tenacity import (
    retry, 
    stop_after_attempt, 
    wait_exponential, 
    retry_if_exception_type,
    before_sleep_log
)
from loguru import logger

def with_retry(
    max_attempts: int = 3,
    wait_multiplier: float = 1.0,
    wait_min: float = 4.0,
    wait_max: float = 10.0,
    retry_exceptions: tuple = (Exception,)
):
    """Decorator for retry logic with exponential backoff."""
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=wait_multiplier, min=wait_min, max=wait_max),
        retry=retry_if_exception_type(retry_exceptions),
        before_sleep=before_sleep_log(logger, "WARNING")
    )

# src/core/error_handler.py
class ErrorHandler:
    """Centralized error handling and recovery."""
    
    def __init__(self, config: Config):
        self.config = config
        self.error_stats = {
            "total_errors": 0,
            "recoverable_errors": 0,
            "critical_errors": 0,
            "errors_by_type": {}
        }
    
    def handle_error(self, error: KindleSyncError, context: Dict[str, Any]) -> bool:
        """Handle error with appropriate recovery strategy."""
        self.error_stats["total_errors"] += 1
        self.error_stats["errors_by_type"][type(error).__name__] = \
            self.error_stats["errors_by_type"].get(type(error).__name__, 0) + 1
        
        if error.severity == ErrorSeverity.CRITICAL:
            self.error_stats["critical_errors"] += 1
            logger.critical(f"Critical error: {error}")
            return False
        
        if error.recoverable:
            self.error_stats["recoverable_errors"] += 1
            logger.warning(f"Recoverable error: {error}")
            return self._attempt_recovery(error, context)
        
        logger.error(f"Non-recoverable error: {error}")
        return False
    
    def _attempt_recovery(self, error: KindleSyncError, context: Dict[str, Any]) -> bool:
        """Attempt to recover from an error."""
        # Implement recovery strategies based on error type
        if isinstance(error, EmailServiceError):
            return self._recover_email_service(error, context)
        elif isinstance(error, FileProcessingError):
            return self._recover_file_processing(error, context)
        
        return False
```

#### Implementation Steps
1. Create custom exception hierarchy
2. Implement retry decorators with exponential backoff
3. Add centralized error handling
4. Update all error-prone operations to use new error handling
5. Add error recovery strategies

#### Reliability Benefits
- 🛡️ Structured error handling with severity levels
- 🛡️ Automatic retry with exponential backoff
- 🛡️ Error recovery strategies
- 🛡️ Comprehensive error statistics and monitoring

### 3. Input Validation & Sanitization

#### Current State
```python
# Limited validation
if not pdf_path.exists():
    logger.error(f"PDF file does not exist: {pdf_path}")
    return False
```

#### Proposed Solution
```python
# src/validation/schemas.py
from pydantic import BaseModel, validator, Field
from pathlib import Path
from typing import List, Optional, Union
import magic
import hashlib

class FileValidationRequest(BaseModel):
    """Request for file validation."""
    file_path: Path
    max_size_mb: int = Field(default=50, ge=1, le=500)
    allowed_extensions: List[str] = Field(default=[".md", ".pdf", ".txt"])
    allowed_mime_types: List[str] = Field(default=[
        "text/markdown",
        "application/pdf",
        "text/plain"
    ])
    
    @validator('file_path')
    def validate_file_path(cls, v):
        if not v.exists():
            raise ValueError("File does not exist")
        if not v.is_file():
            raise ValueError("Path is not a file")
        return v
    
    @validator('file_path')
    def validate_file_size(cls, v, values):
        max_size_bytes = values.get('max_size_mb', 50) * 1024 * 1024
        if v.stat().st_size > max_size_bytes:
            raise ValueError(f"File size exceeds {values.get('max_size_mb', 50)}MB limit")
        return v
    
    @validator('file_path')
    def validate_file_extension(cls, v, values):
        allowed_extensions = values.get('allowed_extensions', [])
        if v.suffix.lower() not in allowed_extensions:
            raise ValueError(f"File extension {v.suffix} not allowed")
        return v

class FileValidator:
    """Comprehensive file validation."""
    
    def __init__(self):
        self.mime_detector = magic.Magic(mime=True)
    
    def validate_file(self, request: FileValidationRequest) -> ValidationResult:
        """Validate file against all criteria."""
        try:
            # Basic validation (handled by Pydantic)
            validated_path = request.file_path
            
            # MIME type validation
            mime_type = self.mime_detector.from_file(str(validated_path))
            if mime_type not in request.allowed_mime_types:
                return ValidationResult(
                    valid=False,
                    error=f"MIME type {mime_type} not allowed"
                )
            
            # Content validation
            if not self._validate_content(validated_path, mime_type):
                return ValidationResult(
                    valid=False,
                    error="File content validation failed"
                )
            
            # Security validation
            if not self._validate_security(validated_path):
                return ValidationResult(
                    valid=False,
                    error="File failed security validation"
                )
            
            return ValidationResult(valid=True, file_path=validated_path)
            
        except Exception as e:
            return ValidationResult(valid=False, error=str(e))
    
    def _validate_content(self, file_path: Path, mime_type: str) -> bool:
        """Validate file content integrity."""
        try:
            if mime_type == "application/pdf":
                return self._validate_pdf_content(file_path)
            elif mime_type == "text/markdown":
                return self._validate_markdown_content(file_path)
            return True
        except Exception:
            return False
    
    def _validate_security(self, file_path: Path) -> bool:
        """Basic security validation."""
        # Check for suspicious patterns
        try:
            with open(file_path, 'rb') as f:
                content = f.read(1024)  # Read first 1KB
                
            # Check for executable signatures
            executable_signatures = [b'\x4d\x5a', b'\x7f\x45\x4c\x46']  # PE, ELF
            for sig in executable_signatures:
                if content.startswith(sig):
                    return False
            
            return True
        except Exception:
            return False

@dataclass
class ValidationResult:
    """Result of file validation."""
    valid: bool
    file_path: Optional[Path] = None
    error: Optional[str] = None
    checksum: Optional[str] = None
```

#### Implementation Steps
1. Create validation schemas with Pydantic
2. Implement comprehensive file validation
3. Add security checks for malicious content
4. Update file processing pipeline to use validation
5. Add validation metrics and monitoring

#### Security Benefits
- 🔒 Comprehensive input validation
- 🔒 MIME type verification
- 🔒 File size limits
- 🔒 Basic security scanning
- 🔒 Content integrity checks

## Medium Priority Improvements

### 4. Async/Await Implementation

#### Current State
```python
# Synchronous processing
def _process_file(self, file_path: Path):
    # Blocking operations
    pdf_path = self.markdown_to_pdf.convert_markdown_to_pdf(markdown_path)
    success = self.kindle_sync.send_pdf_to_kindle(pdf_path)
```

#### Proposed Solution
```python
# src/core/async_processor.py
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional
from pathlib import Path

class AsyncSyncProcessor:
    """Asynchronous file processing with thread pool."""
    
    def __init__(self, config: Config, max_workers: int = 4):
        self.config = config
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.processing_queue = asyncio.Queue()
        self.active_tasks: Dict[str, asyncio.Task] = {}
        
    async def process_file_async(self, file_path: Path) -> ProcessingResult:
        """Process file asynchronously."""
        task_id = f"{file_path.name}_{file_path.stat().st_mtime}"
        
        # Check if already processing
        if task_id in self.active_tasks:
            return ProcessingResult(
                success=False,
                error="File already being processed"
            )
        
        # Create processing task
        task = asyncio.create_task(
            self._process_file_with_retry(file_path)
        )
        self.active_tasks[task_id] = task
        
        try:
            result = await task
            return result
        finally:
            self.active_tasks.pop(task_id, None)
    
    async def _process_file_with_retry(self, file_path: Path) -> ProcessingResult:
        """Process file with retry logic."""
        for attempt in range(3):
            try:
                return await self._process_file_sync(file_path)
            except Exception as e:
                if attempt == 2:  # Last attempt
                    return ProcessingResult(success=False, error=str(e))
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
    
    async def _process_file_sync(self, file_path: Path) -> ProcessingResult:
        """Process file using thread pool for CPU-bound operations."""
        loop = asyncio.get_event_loop()
        
        # Run CPU-intensive operations in thread pool
        if file_path.suffix.lower() == ".md":
            pdf_path = await loop.run_in_executor(
                self.executor,
                self._convert_markdown_to_pdf,
                file_path
            )
            
            # Send to Kindle (I/O bound)
            success = await self._send_pdf_to_kindle_async(pdf_path)
            return ProcessingResult(success=success, data=pdf_path)
        
        elif file_path.suffix.lower() == ".pdf":
            markdown_path = await loop.run_in_executor(
                self.executor,
                self._convert_pdf_to_markdown,
                file_path
            )
            return ProcessingResult(success=True, data=markdown_path)
        
        return ProcessingResult(success=False, error="Unsupported file type")
    
    async def _send_pdf_to_kindle_async(self, pdf_path: Path) -> bool:
        """Send PDF to Kindle asynchronously."""
        # Use aiohttp for async HTTP requests if needed
        # or run SMTP in thread pool
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self.kindle_sync.send_pdf_to_kindle,
            pdf_path
        )

# src/core/async_file_watcher.py
class AsyncFileWatcher:
    """Asynchronous file watcher with queue-based processing."""
    
    def __init__(self, config: Config, processor: AsyncSyncProcessor):
        self.config = config
        self.processor = processor
        self.observer = None
        self.processing_queue = asyncio.Queue(maxsize=100)
        self.running = False
    
    async def start(self):
        """Start async file watching."""
        self.running = True
        
        # Start file system observer
        self.observer = Observer()
        handler = AsyncFileHandler(self.processing_queue)
        self.observer.schedule(handler, str(self.config.get_obsidian_vault_path()), recursive=True)
        self.observer.start()
        
        # Start processing workers
        workers = [
            asyncio.create_task(self._process_queue())
            for _ in range(3)  # 3 concurrent workers
        ]
        
        await asyncio.gather(*workers)
    
    async def _process_queue(self):
        """Process files from the queue."""
        while self.running:
            try:
                file_path = await asyncio.wait_for(
                    self.processing_queue.get(), 
                    timeout=1.0
                )
                await self.processor.process_file_async(file_path)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error processing file from queue: {e}")
```

#### Implementation Steps
1. Create async processor with thread pool
2. Implement async file watcher
3. Add async email sending capabilities
4. Update main application loop to be async
5. Add performance monitoring for async operations

#### Performance Benefits
- ⚡ 3-5x improvement in concurrent file processing
- ⚡ Non-blocking I/O operations
- ⚡ Better resource utilization
- ⚡ Improved responsiveness

### 5. Database Integration

#### Current State
```python
# No persistent state
self.stats = {
    "files_processed": 0,
    "pdfs_generated": 0,
    # ... in-memory only
}
```

#### Proposed Solution
```python
# src/database/models.py
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy import create_engine
from datetime import datetime
from pathlib import Path

Base = declarative_base()

class ProcessedFile(Base):
    """Model for tracking processed files."""
    __tablename__ = 'processed_files'
    
    id = Column(Integer, primary_key=True)
    file_path = Column(String(500), unique=True, nullable=False)
    file_hash = Column(String(64), nullable=False)  # SHA-256
    file_size = Column(Integer, nullable=False)
    file_type = Column(String(10), nullable=False)  # .md, .pdf
    processed_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String(20), nullable=False)  # success, failed, processing
    error_message = Column(Text, nullable=True)
    processing_time_ms = Column(Integer, nullable=True)
    
    # Relationships
    operations = relationship("FileOperation", back_populates="file")

class FileOperation(Base):
    """Model for tracking individual operations on files."""
    __tablename__ = 'file_operations'
    
    id = Column(Integer, primary_key=True)
    file_id = Column(Integer, ForeignKey('processed_files.id'), nullable=False)
    operation_type = Column(String(50), nullable=False)  # convert_to_pdf, send_to_kindle, etc.
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    success = Column(Boolean, nullable=False)
    error_message = Column(Text, nullable=True)
    metadata = Column(Text, nullable=True)  # JSON string for additional data
    
    # Relationships
    file = relationship("ProcessedFile", back_populates="operations")

class SystemStats(Base):
    """Model for system statistics."""
    __tablename__ = 'system_stats'
    
    id = Column(Integer, primary_key=True)
    metric_name = Column(String(100), nullable=False)
    metric_value = Column(Integer, nullable=False)
    recorded_at = Column(DateTime, default=datetime.utcnow)
    tags = Column(Text, nullable=True)  # JSON string for tags

# src/database/manager.py
class DatabaseManager:
    """Database manager for Kindle Sync application."""
    
    def __init__(self, db_path: str = "kindle_sync.db"):
        self.db_path = db_path
        self.engine = create_engine(f"sqlite:///{db_path}")
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        # Create tables
        Base.metadata.create_all(bind=self.engine)
    
    def get_session(self):
        """Get database session."""
        return self.SessionLocal()
    
    def record_file_processed(self, file_path: Path, status: str, 
                            processing_time_ms: int = None, error_message: str = None):
        """Record a processed file."""
        with self.get_session() as session:
            file_hash = self._calculate_file_hash(file_path)
            file_size = file_path.stat().st_size
            
            processed_file = ProcessedFile(
                file_path=str(file_path),
                file_hash=file_hash,
                file_size=file_size,
                file_type=file_path.suffix,
                status=status,
                processing_time_ms=processing_time_ms,
                error_message=error_message
            )
            
            session.add(processed_file)
            session.commit()
    
    def record_operation(self, file_path: Path, operation_type: str, 
                        success: bool, error_message: str = None, metadata: dict = None):
        """Record an operation on a file."""
        with self.get_session() as session:
            # Find the file record
            file_record = session.query(ProcessedFile).filter(
                ProcessedFile.file_path == str(file_path)
            ).first()
            
            if file_record:
                operation = FileOperation(
                    file_id=file_record.id,
                    operation_type=operation_type,
                    success=success,
                    error_message=error_message,
                    metadata=json.dumps(metadata) if metadata else None
                )
                session.add(operation)
                session.commit()
    
    def get_processing_stats(self) -> dict:
        """Get processing statistics from database."""
        with self.get_session() as session:
            stats = {}
            
            # Total files processed
            stats['total_files'] = session.query(ProcessedFile).count()
            
            # Success rate
            successful = session.query(ProcessedFile).filter(
                ProcessedFile.status == 'success'
            ).count()
            stats['success_rate'] = (successful / stats['total_files'] * 100) if stats['total_files'] > 0 else 0
            
            # Average processing time
            avg_time = session.query(ProcessedFile).filter(
                ProcessedFile.processing_time_ms.isnot(None)
            ).with_entities(
                func.avg(ProcessedFile.processing_time_ms)
            ).scalar()
            stats['avg_processing_time_ms'] = avg_time or 0
            
            return stats
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of file."""
        import hashlib
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
```

#### Implementation Steps
1. Design database schema
2. Implement SQLAlchemy models
3. Create database manager
4. Update file processing to record operations
5. Add database migration system
6. Implement backup and recovery

#### Benefits
- 📊 Persistent state across restarts
- 📊 Detailed operation tracking
- 📊 Historical statistics and analytics
- 📊 Audit trail for troubleshooting
- 📊 Performance metrics collection

### 6. Health Checks & Monitoring

#### Current State
```dockerfile
# Basic health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"
```

#### Proposed Solution
```python
# src/monitoring/health.py
from enum import Enum
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
import psutil
import shutil
from pathlib import Path

class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"

@dataclass
class HealthCheck:
    """Individual health check result."""
    name: str
    status: HealthStatus
    message: str
    details: Optional[Dict[str, Any]] = None
    response_time_ms: Optional[float] = None

@dataclass
class HealthReport:
    """Overall health report."""
    overall_status: HealthStatus
    checks: List[HealthCheck]
    timestamp: datetime
    version: str

class HealthMonitor:
    """Comprehensive health monitoring system."""
    
    def __init__(self, config: Config):
        self.config = config
        self.checks = {
            'file_watcher': self._check_file_watcher,
            'email_service': self._check_email_service,
            'disk_space': self._check_disk_space,
            'memory_usage': self._check_memory_usage,
            'database': self._check_database,
            'file_permissions': self._check_file_permissions,
            'network_connectivity': self._check_network_connectivity,
        }
    
    def get_health_report(self) -> HealthReport:
        """Get comprehensive health report."""
        checks = []
        
        for name, check_func in self.checks.items():
            try:
                start_time = time.time()
                check_result = check_func()
                response_time = (time.time() - start_time) * 1000
                
                check_result.response_time_ms = response_time
                checks.append(check_result)
            except Exception as e:
                checks.append(HealthCheck(
                    name=name,
                    status=HealthStatus.CRITICAL,
                    message=f"Health check failed: {e}",
                    response_time_ms=None
                ))
        
        # Determine overall status
        overall_status = self._determine_overall_status(checks)
        
        return HealthReport(
            overall_status=overall_status,
            checks=checks,
            timestamp=datetime.utcnow(),
            version=self._get_version()
        )
    
    def _check_file_watcher(self) -> HealthCheck:
        """Check file watcher health."""
        try:
            # Check if file watcher is running
            if not hasattr(self, 'file_watcher') or not self.file_watcher.is_alive():
                return HealthCheck(
                    name='file_watcher',
                    status=HealthStatus.CRITICAL,
                    message="File watcher is not running"
                )
            
            # Check if it can access the vault
            vault_path = self.config.get_obsidian_vault_path()
            if not vault_path.exists():
                return HealthCheck(
                    name='file_watcher',
                    status=HealthStatus.CRITICAL,
                    message=f"Obsidian vault not accessible: {vault_path}"
                )
            
            return HealthCheck(
                name='file_watcher',
                status=HealthStatus.HEALTHY,
                message="File watcher is running normally"
            )
        except Exception as e:
            return HealthCheck(
                name='file_watcher',
                status=HealthStatus.CRITICAL,
                message=f"File watcher check failed: {e}"
            )
    
    def _check_email_service(self) -> HealthCheck:
        """Check email service connectivity."""
        try:
            smtp_config = self.config.get_smtp_config()
            
            # Test SMTP connection
            import smtplib
            server = smtplib.SMTP(smtp_config['server'], smtp_config['port'])
            server.starttls()
            server.login(smtp_config['username'], smtp_config['password'])
            server.quit()
            
            return HealthCheck(
                name='email_service',
                status=HealthStatus.HEALTHY,
                message="Email service is accessible"
            )
        except Exception as e:
            return HealthCheck(
                name='email_service',
                status=HealthStatus.UNHEALTHY,
                message=f"Email service check failed: {e}"
            )
    
    def _check_disk_space(self) -> HealthCheck:
        """Check available disk space."""
        try:
            vault_path = self.config.get_obsidian_vault_path()
            total, used, free = shutil.disk_usage(vault_path)
            
            free_gb = free / (1024**3)
            total_gb = total / (1024**3)
            usage_percent = (used / total) * 100
            
            if usage_percent > 90:
                status = HealthStatus.CRITICAL
                message = f"Disk space critically low: {free_gb:.1f}GB free ({usage_percent:.1f}% used)"
            elif usage_percent > 80:
                status = HealthStatus.DEGRADED
                message = f"Disk space low: {free_gb:.1f}GB free ({usage_percent:.1f}% used)"
            else:
                status = HealthStatus.HEALTHY
                message = f"Disk space OK: {free_gb:.1f}GB free ({usage_percent:.1f}% used)"
            
            return HealthCheck(
                name='disk_space',
                status=status,
                message=message,
                details={
                    'free_gb': free_gb,
                    'total_gb': total_gb,
                    'usage_percent': usage_percent
                }
            )
        except Exception as e:
            return HealthCheck(
                name='disk_space',
                status=HealthStatus.CRITICAL,
                message=f"Disk space check failed: {e}"
            )
    
    def _check_memory_usage(self) -> HealthCheck:
        """Check memory usage."""
        try:
            memory = psutil.virtual_memory()
            usage_percent = memory.percent
            
            if usage_percent > 90:
                status = HealthStatus.CRITICAL
                message = f"Memory usage critically high: {usage_percent:.1f}%"
            elif usage_percent > 80:
                status = HealthStatus.DEGRADED
                message = f"Memory usage high: {usage_percent:.1f}%"
            else:
                status = HealthStatus.HEALTHY
                message = f"Memory usage normal: {usage_percent:.1f}%"
            
            return HealthCheck(
                name='memory_usage',
                status=status,
                message=message,
                details={
                    'usage_percent': usage_percent,
                    'available_gb': memory.available / (1024**3),
                    'total_gb': memory.total / (1024**3)
                }
            )
        except Exception as e:
            return HealthCheck(
                name='memory_usage',
                status=HealthStatus.CRITICAL,
                message=f"Memory check failed: {e}"
            )

# src/api/health_endpoint.py
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

app = FastAPI(title="Kindle Sync Health API")

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        health_report = health_monitor.get_health_report()
        
        status_code = 200
        if health_report.overall_status == HealthStatus.CRITICAL:
            status_code = 503
        elif health_report.overall_status == HealthStatus.UNHEALTHY:
            status_code = 503
        elif health_report.overall_status == HealthStatus.DEGRADED:
            status_code = 200  # Still operational
        
        return JSONResponse(
            status_code=status_code,
            content=health_report.__dict__
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health/ready")
async def readiness_check():
    """Readiness check for Kubernetes."""
    health_report = health_monitor.get_health_report()
    
    # Consider system ready if not critical
    if health_report.overall_status == HealthStatus.CRITICAL:
        raise HTTPException(status_code=503, detail="System not ready")
    
    return {"status": "ready"}

@app.get("/health/live")
async def liveness_check():
    """Liveness check for Kubernetes."""
    # Simple check - if we can respond, we're alive
    return {"status": "alive"}
```

#### Implementation Steps
1. Create health monitoring system
2. Implement individual health checks
3. Add FastAPI health endpoints
4. Update Docker health check
5. Add health monitoring to main application
6. Create health dashboard

#### Benefits
- 📊 Comprehensive system monitoring
- 📊 Proactive issue detection
- 📊 Kubernetes-ready health checks
- 📊 Performance metrics collection
- 📊 Automated alerting capabilities

## Low Priority Improvements

### 7. Type Hints & Documentation

#### Current State
```python
# Inconsistent type hints
def get(self, key: str, default: Any = None) -> Any:
def _process_file(self, file_path: Path):
```

#### Proposed Solution
```python
# src/types/protocols.py
from typing import Protocol, TypeVar, Generic, Union, Optional, List, Dict, Any
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

T = TypeVar('T')
ProcessingResultType = TypeVar('ProcessingResultType')

class FileProcessor(Protocol):
    """Protocol for file processors."""
    
    def can_process(self, file_path: Path) -> bool:
        """Check if processor can handle the file."""
        ...
    
    def process(self, file_path: Path) -> 'ProcessingResult[Path]':
        """Process the file."""
        ...

class EmailService(Protocol):
    """Protocol for email services."""
    
    def send_email(self, to: str, subject: str, body: str, 
                   attachments: Optional[List[Path]] = None) -> bool:
        """Send email with optional attachments."""
        ...

@dataclass(frozen=True)
class ProcessingResult(Generic[T]):
    """Result of a processing operation."""
    success: bool
    data: Optional[T] = None
    error: Optional[str] = None
    processing_time_ms: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None
    
    @classmethod
    def success_result(cls, data: T, processing_time_ms: float = None, 
                      metadata: Dict[str, Any] = None) -> 'ProcessingResult[T]':
        """Create a successful result."""
        return cls(
            success=True,
            data=data,
            processing_time_ms=processing_time_ms,
            metadata=metadata
        )
    
    @classmethod
    def error_result(cls, error: str, metadata: Dict[str, Any] = None) -> 'ProcessingResult[T]':
        """Create an error result."""
        return cls(
            success=False,
            error=error,
            metadata=metadata
        )

class FileType(Enum):
    """Supported file types."""
    MARKDOWN = "markdown"
    PDF = "pdf"
    TEXT = "text"
    UNKNOWN = "unknown"

@dataclass(frozen=True)
class FileMetadata:
    """Metadata for a file."""
    path: Path
    size_bytes: int
    file_type: FileType
    mime_type: str
    checksum: str
    created_at: datetime
    modified_at: datetime
    
    @classmethod
    def from_path(cls, path: Path) -> 'FileMetadata':
        """Create metadata from file path."""
        stat = path.stat()
        return cls(
            path=path,
            size_bytes=stat.st_size,
            file_type=cls._determine_file_type(path),
            mime_type=cls._get_mime_type(path),
            checksum=cls._calculate_checksum(path),
            created_at=datetime.fromtimestamp(stat.st_ctime),
            modified_at=datetime.fromtimestamp(stat.st_mtime)
        )

# Enhanced type hints throughout the codebase
class Config:
    def get_obsidian_vault_path(self) -> Path:
        """Get the Obsidian vault path."""
        return Path(self.get("obsidian.vault_path", ""))
    
    def get_smtp_config(self) -> Dict[str, Union[str, int]]:
        """Get SMTP configuration with proper typing."""
        return {
            "server": self.get("kindle.smtp_server", ""),
            "port": int(self.get("kindle.smtp_port", 587)),
            "username": self.get("kindle.smtp_username", ""),
            "password": self.get("kindle.smtp_password", ""),
        }
```

#### Implementation Steps
1. Create comprehensive type definitions
2. Add protocols for interfaces
3. Update all function signatures with proper types
4. Add mypy configuration
5. Run type checking in CI/CD
6. Update documentation with type information

#### Benefits
- 🔍 Better IDE support and autocomplete
- 🔍 Catch type-related bugs at development time
- 🔍 Improved code documentation
- 🔍 Better refactoring safety
- 🔍 Enhanced developer experience

### 8. Configuration Schema Validation

#### Current State
```python
# Basic YAML loading
config = yaml.safe_load(f)
```

#### Proposed Solution
```python
# src/config/schemas.py
from pydantic import BaseSettings, Field, validator, root_validator
from pathlib import Path
from typing import List, Optional, Union, Dict, Any
import os

class ObsidianConfig(BaseSettings):
    """Obsidian configuration schema."""
    vault_path: Path = Field(..., description="Path to Obsidian vault")
    sync_folder: str = Field(default="Kindle Sync", description="Sync folder name")
    templates_folder: str = Field(default="Templates", description="Templates folder name")
    watch_subfolders: bool = Field(default=True, description="Watch subfolders")
    
    @validator('vault_path')
    def validate_vault_path(cls, v):
        if not v.exists():
            raise ValueError(f"Obsidian vault path does not exist: {v}")
        if not v.is_dir():
            raise ValueError(f"Obsidian vault path is not a directory: {v}")
        return v
    
    class Config:
        env_prefix = "OBSIDIAN_"

class KindleConfig(BaseSettings):
    """Kindle configuration schema."""
    email: str = Field(..., description="Kindle email address")
    approved_senders: List[str] = Field(default_factory=list, description="Approved email senders")
    usb_path: Optional[Path] = Field(default=None, description="USB mount path")
    
    @validator('email')
    def validate_email(cls, v):
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, v):
            raise ValueError(f"Invalid email format: {v}")
        return v
    
    class Config:
        env_prefix = "KINDLE_"

class SMTPConfig(BaseSettings):
    """SMTP configuration schema."""
    host: str = Field(..., description="SMTP server host")
    port: int = Field(default=587, ge=1, le=65535, description="SMTP server port")
    username: str = Field(..., description="SMTP username")
    password: str = Field(..., description="SMTP password")
    use_tls: bool = Field(default=True, description="Use TLS encryption")
    
    class Config:
        env_prefix = "SMTP_"

class ProcessingConfig(BaseSettings):
    """File processing configuration schema."""
    max_file_size_mb: int = Field(default=50, ge=1, le=500, description="Maximum file size in MB")
    concurrent_processing: bool = Field(default=True, description="Enable concurrent processing")
    retry_attempts: int = Field(default=3, ge=1, le=10, description="Number of retry attempts")
    debounce_time: float = Field(default=2.0, ge=0.1, le=10.0, description="File change debounce time")
    
    class Config:
        env_prefix = "PROCESSING_"

class LoggingConfig(BaseSettings):
    """Logging configuration schema."""
    level: str = Field(default="INFO", description="Logging level")
    file: str = Field(default="kindle_sync.log", description="Log file path")
    max_size: str = Field(default="10MB", description="Maximum log file size")
    backup_count: int = Field(default=5, ge=1, le=20, description="Number of backup log files")
    
    @validator('level')
    def validate_level(cls, v):
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid logging level: {v}. Must be one of {valid_levels}")
        return v.upper()
    
    class Config:
        env_prefix = "LOGGING_"

class KindleSyncConfig(BaseSettings):
    """Main configuration schema."""
    obsidian: ObsidianConfig
    kindle: KindleConfig
    smtp: SMTPConfig
    processing: ProcessingConfig
    logging: LoggingConfig
    
    # Advanced settings
    advanced: Dict[str, Any] = Field(default_factory=dict)
    
    @root_validator
    def validate_configuration(cls, values):
        """Validate entire configuration."""
        # Check if approved senders include SMTP username
        smtp_username = values.get('smtp', {}).get('username', '')
        approved_senders = values.get('kindle', {}).get('approved_senders', [])
        
        if smtp_username and smtp_username not in approved_senders:
            logger.warning(f"SMTP username {smtp_username} not in approved senders list")
        
        return values
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

# src/config/validator.py
class ConfigValidator:
    """Configuration validation and loading."""
    
    @staticmethod
    def load_and_validate(config_path: str) -> KindleSyncConfig:
        """Load and validate configuration from file."""
        try:
            # Load YAML file
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
            
            # Convert to Pydantic model
            config = KindleSyncConfig(**config_data)
            
            # Additional validation
            ConfigValidator._validate_paths(config)
            ConfigValidator._validate_connectivity(config)
            
            logger.info("Configuration validation successful")
            return config
            
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Invalid YAML configuration: {e}")
        except ValidationError as e:
            raise ConfigurationError(f"Configuration validation failed: {e}")
        except Exception as e:
            raise ConfigurationError(f"Configuration loading failed: {e}")
    
    @staticmethod
    def _validate_paths(config: KindleSyncConfig):
        """Validate file paths."""
        # Check vault path
        if not config.obsidian.vault_path.exists():
            raise ConfigurationError(f"Obsidian vault path does not exist: {config.obsidian.vault_path}")
        
        # Check USB path if specified
        if config.kindle.usb_path and not config.kindle.usb_path.exists():
            logger.warning(f"Kindle USB path does not exist: {config.kindle.usb_path}")
    
    @staticmethod
    def _validate_connectivity(config: KindleSyncConfig):
        """Validate network connectivity."""
        try:
            # Test SMTP connection
            import smtplib
            server = smtplib.SMTP(config.smtp.host, config.smtp.port)
            server.starttls()
            server.login(config.smtp.username, config.smtp.password)
            server.quit()
            logger.info("SMTP connectivity validation successful")
        except Exception as e:
            logger.warning(f"SMTP connectivity validation failed: {e}")
```

#### Implementation Steps
1. Create Pydantic configuration schemas
2. Implement configuration validation
3. Add environment variable support
4. Update configuration loading
5. Add configuration migration system
6. Update documentation

#### Benefits
- ✅ Type-safe configuration
- ✅ Automatic validation
- ✅ Environment variable support
- ✅ Clear error messages
- ✅ IDE autocomplete support

### 9. Plugin Architecture

#### Current State
```python
# Monolithic processing
def _process_file(self, file_path: Path):
    if file_path.suffix.lower() == ".md":
        self._process_markdown_file(file_path)
    elif file_path.suffix.lower() == ".pdf":
        self._process_pdf_file(file_path)
```

#### Proposed Solution
```python
# src/plugins/base.py
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from pathlib import Path
from .types import ProcessingResult, FileMetadata

class FileProcessorPlugin(ABC):
    """Base class for file processor plugins."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Plugin name."""
        pass
    
    @property
    @abstractmethod
    def version(self) -> str:
        """Plugin version."""
        pass
    
    @property
    @abstractmethod
    def supported_extensions(self) -> List[str]:
        """List of supported file extensions."""
        pass
    
    @abstractmethod
    def can_process(self, file_metadata: FileMetadata) -> bool:
        """Check if plugin can process the file."""
        pass
    
    @abstractmethod
    def process(self, file_metadata: FileMetadata, 
                config: Dict[str, Any]) -> ProcessingResult:
        """Process the file."""
        pass
    
    def get_priority(self) -> int:
        """Get plugin priority (higher = more priority)."""
        return 100
    
    def get_config_schema(self) -> Dict[str, Any]:
        """Get plugin configuration schema."""
        return {}

# src/plugins/markdown_processor.py
class MarkdownToPDFPlugin(FileProcessorPlugin):
    """Plugin for converting Markdown to PDF."""
    
    @property
    def name(self) -> str:
        return "markdown-to-pdf"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    @property
    def supported_extensions(self) -> List[str]:
        return [".md", ".markdown"]
    
    def can_process(self, file_metadata: FileMetadata) -> bool:
        return file_metadata.file_type == FileType.MARKDOWN
    
    def process(self, file_metadata: FileMetadata, 
                config: Dict[str, Any]) -> ProcessingResult:
        """Convert Markdown to PDF."""
        try:
            start_time = time.time()
            
            # Load configuration
            pdf_config = config.get('pdf', {})
            
            # Convert to PDF
            converter = MarkdownToPDFConverter(pdf_config)
            pdf_path = converter.convert(file_metadata.path)
            
            processing_time = (time.time() - start_time) * 1000
            
            return ProcessingResult.success_result(
                data=pdf_path,
                processing_time_ms=processing_time,
                metadata={'plugin': self.name, 'version': self.version}
            )
            
        except Exception as e:
            return ProcessingResult.error_result(
                error=f"Markdown to PDF conversion failed: {e}",
                metadata={'plugin': self.name, 'version': self.version}
            )

# src/plugins/pdf_processor.py
class PDFToMarkdownPlugin(FileProcessorPlugin):
    """Plugin for converting PDF to Markdown."""
    
    @property
    def name(self) -> str:
        return "pdf-to-markdown"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    @property
    def supported_extensions(self) -> List[str]:
        return [".pdf"]
    
    def can_process(self, file_metadata: FileMetadata) -> bool:
        return file_metadata.file_type == FileType.PDF
    
    def process(self, file_metadata: FileMetadata, 
                config: Dict[str, Any]) -> ProcessingResult:
        """Convert PDF to Markdown."""
        try:
            start_time = time.time()
            
            # Load configuration
            ocr_config = config.get('ocr', {})
            
            # Convert to Markdown
            converter = PDFToMarkdownConverter(ocr_config)
            markdown_path = converter.convert(file_metadata.path)
            
            processing_time = (time.time() - start_time) * 1000
            
            return ProcessingResult.success_result(
                data=markdown_path,
                processing_time_ms=processing_time,
                metadata={'plugin': self.name, 'version': self.version}
            )
            
        except Exception as e:
            return ProcessingResult.error_result(
                error=f"PDF to Markdown conversion failed: {e}",
                metadata={'plugin': self.name, 'version': self.version}
            )

# src/plugins/manager.py
class PluginManager:
    """Manages file processor plugins."""
    
    def __init__(self, config: KindleSyncConfig):
        self.config = config
        self.plugins: List[FileProcessorPlugin] = []
        self._load_builtin_plugins()
        self._load_external_plugins()
    
    def _load_builtin_plugins(self):
        """Load built-in plugins."""
        self.plugins.extend([
            MarkdownToPDFPlugin(),
            PDFToMarkdownPlugin(),
            EmailSenderPlugin(),
            BackupPlugin(),
        ])
    
    def _load_external_plugins(self):
        """Load external plugins from plugins directory."""
        plugins_dir = Path("plugins")
        if not plugins_dir.exists():
            return
        
        for plugin_file in plugins_dir.glob("*.py"):
            try:
                plugin_module = importlib.import_module(f"plugins.{plugin_file.stem}")
                for attr_name in dir(plugin_module):
                    attr = getattr(plugin_module, attr_name)
                    if (isinstance(attr, type) and 
                        issubclass(attr, FileProcessorPlugin) and 
                        attr != FileProcessorPlugin):
                        plugin_instance = attr()
                        self.plugins.append(plugin_instance)
                        logger.info(f"Loaded external plugin: {plugin_instance.name}")
            except Exception as e:
                logger.error(f"Failed to load plugin {plugin_file}: {e}")
    
    def get_plugin_for_file(self, file_metadata: FileMetadata) -> Optional[FileProcessorPlugin]:
        """Get the best plugin for processing a file."""
        suitable_plugins = [
            plugin for plugin in self.plugins
            if plugin.can_process(file_metadata)
        ]
        
        if not suitable_plugins:
            return None
        
        # Return plugin with highest priority
        return max(suitable_plugins, key=lambda p: p.get_priority())
    
    def process_file(self, file_metadata: FileMetadata) -> ProcessingResult:
        """Process file using appropriate plugin."""
        plugin = self.get_plugin_for_file(file_metadata)
        
        if not plugin:
            return ProcessingResult.error_result(
                error=f"No plugin available for file type: {file_metadata.file_type}"
            )
        
        try:
            # Get plugin-specific configuration
            plugin_config = self.config.advanced.get('plugins', {}).get(plugin.name, {})
            
            # Process file
            result = plugin.process(file_metadata, plugin_config)
            
            # Record plugin usage
            self._record_plugin_usage(plugin, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Plugin {plugin.name} failed to process file: {e}")
            return ProcessingResult.error_result(
                error=f"Plugin processing failed: {e}",
                metadata={'plugin': plugin.name}
            )
    
    def _record_plugin_usage(self, plugin: FileProcessorPlugin, result: ProcessingResult):
        """Record plugin usage statistics."""
        # Implementation for tracking plugin performance
        pass
    
    def get_plugin_info(self) -> List[Dict[str, Any]]:
        """Get information about all loaded plugins."""
        return [
            {
                'name': plugin.name,
                'version': plugin.version,
                'supported_extensions': plugin.supported_extensions,
                'priority': plugin.get_priority()
            }
            for plugin in self.plugins
        ]
```

#### Implementation Steps
1. Create plugin base classes and interfaces
2. Convert existing processors to plugins
3. Implement plugin manager
4. Add plugin discovery and loading
5. Create plugin configuration system
6. Add plugin development documentation

#### Benefits
- 🔌 Modular and extensible architecture
- 🔌 Easy to add new file processors
- 🔌 Plugin isolation and error handling
- 🔌 Plugin priority and selection
- 🔌 External plugin support

## Infrastructure & DevOps

### 10. Enhanced Docker Configuration

#### Current State
```dockerfile
# Basic multi-stage build
FROM python:3.11-slim-bullseye as base
# ... basic setup
```

#### Proposed Solution
```dockerfile
# Multi-stage build with security and optimization
FROM python:3.11-slim-bullseye as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
COPY requirements.txt requirements-test.txt ./
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.11-slim-bullseye as production

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    poppler-utils \
    libgl1 \
    libglx-mesa0 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgcc-s1 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create non-root user with specific UID/GID
RUN groupadd -r kindlesync -g 1000 && \
    useradd -r -g kindlesync -u 1000 -d /app -s /bin/bash kindlesync

# Create application directory
WORKDIR /app

# Copy application code
COPY --chown=kindlesync:kindlesync . .

# Create necessary directories with proper permissions
RUN mkdir -p /app/logs /app/backups /app/data /app/temp && \
    chown -R kindlesync:kindlesync /app

# Switch to non-root user
USER kindlesync

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    TZ=UTC

# Expose health check port
EXPOSE 8000

# Add comprehensive health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Add labels for better container management
LABEL maintainer="kindle-sync-team" \
      version="1.0.0" \
      description="Kindle Scribe ↔ Obsidian Sync System" \
      org.opencontainers.image.source="https://github.com/haydentwestbrook/kindle-sync"

# Default command
CMD ["python", "main.py", "start"]

# Development stage
FROM production as development

# Install development dependencies
USER root
RUN apt-get update && apt-get install -y \
    git \
    vim \
    htop \
    && rm -rf /var/lib/apt/lists/*

# Install development Python packages
USER kindlesync
RUN pip install --no-cache-dir -r requirements-test.txt

# Override command for development
CMD ["python", "main.py", "start", "--debug"]
```

#### Docker Compose Enhancement
```yaml
# docker-compose.yml
version: '3.8'

services:
  kindle-sync:
    build:
      context: .
      target: production
      args:
        BUILD_DATE: ${BUILD_DATE}
        VCS_REF: ${VCS_REF}
    container_name: kindle-sync
    restart: unless-stopped
    
    # Resource limits for Raspberry Pi
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '0.5'
        reservations:
          memory: 256M
          cpus: '0.25'
    
    # Environment variables
    environment:
      - TZ=${TZ:-UTC}
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
      - SMTP_PASSWORD=${SMTP_PASSWORD}
      - KINDLE_EMAIL=${KINDLE_EMAIL}
    
    # Volume mounts
    volumes:
      - ${OBSIDIAN_VAULT_PATH}:/app/data/obsidian:rw
      - ./config.yaml:/app/config.yaml:ro
      - ./logs:/app/logs:rw
      - ./backups:/app/backups:rw
      - ./temp:/app/temp:rw
      - kindle-sync-data:/app/data
    
    # Ports
    ports:
      - "8000:8000"  # Health check endpoint
    
    # Health check
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 5s
    
    # Logging
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
    
    # Security
    security_opt:
      - no-new-privileges:true
    
    # Capabilities
    cap_drop:
      - ALL
    cap_add:
      - CHOWN
      - SETGID
      - SETUID

  # Optional: Database for state management
  postgres:
    image: postgres:15-alpine
    container_name: kindle-sync-db
    restart: unless-stopped
    environment:
      - POSTGRES_DB=kindle_sync
      - POSTGRES_USER=kindle_sync
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    volumes:
      - postgres-data:/var/lib/postgresql/data
    deploy:
      resources:
        limits:
          memory: 256M
          cpus: '0.25'

volumes:
  kindle-sync-data:
    driver: local
  postgres-data:
    driver: local

networks:
  default:
    name: kindle-sync-network
```

#### Implementation Steps
1. Create multi-stage Dockerfile with security improvements
2. Add comprehensive health checks
3. Implement proper user management
4. Add resource limits for Raspberry Pi
5. Create development and production targets
6. Update docker-compose with enhanced configuration

#### Benefits
- 🐳 Optimized image size and build time
- 🐳 Enhanced security with non-root user
- 🐳 Comprehensive health monitoring
- 🐳 Resource limits for Raspberry Pi
- 🐳 Development and production environments

### 11. CI/CD Pipeline Enhancements

#### Current State
```yaml
# Basic GitHub Actions workflow
name: Test Suite
on: [push, pull_request]
```

#### Proposed Solution
```yaml
# .github/workflows/ci.yml
name: Continuous Integration

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM UTC

env:
  PYTHON_VERSION: '3.11'
  NODE_VERSION: '18'
  DOCKER_BUILDKIT: 1

jobs:
  # Code Quality Checks
  code-quality:
    name: Code Quality
    runs-on: ubuntu-latest
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v4
      with:
        fetch-depth: 0  # Full history for better analysis
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ env.PYTHON_VERSION }}
        cache: 'pip'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r requirements-test.txt
        pip install black isort flake8 mypy bandit safety
    
    - name: Code formatting (Black)
      run: black --check --diff .
    
    - name: Import sorting (isort)
      run: isort --check-only --diff .
    
    - name: Linting (flake8)
      run: flake8 src tests
    
    - name: Type checking (mypy)
      run: mypy src
    
    - name: Security scan (bandit)
      run: bandit -r src -f json -o bandit-report.json
    
    - name: Dependency vulnerability scan (safety)
      run: safety check --json --output safety-report.json
    
    - name: Upload security reports
      uses: actions/upload-artifact@v4
      if: always()
      with:
        name: security-reports
        path: |
          bandit-report.json
          safety-report.json

  # Unit Tests
  unit-tests:
    name: Unit Tests
    runs-on: ubuntu-latest
    needs: code-quality
    
    strategy:
      matrix:
        python-version: ['3.9', '3.10', '3.11']
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v4
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
        cache: 'pip'
    
    - name: Install system dependencies
      run: |
        sudo apt-get update
        sudo apt-get install -y tesseract-ocr tesseract-ocr-eng poppler-utils
    
    - name: Install Python dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r requirements-test.txt
    
    - name: Run unit tests
      run: |
        python -m pytest tests/unit/ \
          -v \
          --cov=src \
          --cov-report=xml \
          --cov-report=term-missing \
          --junitxml=test-results-unit.xml \
          --maxfail=5
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v4
      with:
        file: ./coverage.xml
        flags: unit
        name: unit-tests-${{ matrix.python-version }}
    
    - name: Upload test results
      uses: actions/upload-artifact@v4
      if: always()
      with:
        name: unit-test-results-${{ matrix.python-version }}
        path: |
          test-results-unit.xml
          coverage.xml

  # Integration Tests
  integration-tests:
    name: Integration Tests
    runs-on: ubuntu-latest
    needs: unit-tests
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: test_kindle_sync
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ env.PYTHON_VERSION }}
        cache: 'pip'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r requirements-test.txt
    
    - name: Run integration tests
      run: |
        python -m pytest tests/integration/ \
          -v \
          --junitxml=test-results-integration.xml
    
    - name: Upload test results
      uses: actions/upload-artifact@v4
      if: always()
      with:
        name: integration-test-results
        path: test-results-integration.xml

  # Docker Build and Test
  docker-build:
    name: Docker Build
    runs-on: ubuntu-latest
    needs: [unit-tests, integration-tests]
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v4
    
    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v3
    
    - name: Build Docker image
      uses: docker/build-push-action@v5
      with:
        context: .
        target: production
        push: false
        tags: kindle-sync:test
        cache-from: type=gha
        cache-to: type=gha,mode=max
        build-args: |
          BUILD_DATE=${{ github.event.head_commit.timestamp }}
          VCS_REF=${{ github.sha }}
    
    - name: Test Docker image
      run: |
        docker run --rm kindle-sync:test python -c "import sys; print('Python version:', sys.version)"
        docker run --rm kindle-sync:test python -m pytest tests/unit/ -v

  # Security Scan
  security-scan:
    name: Security Scan
    runs-on: ubuntu-latest
    needs: docker-build
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v4
    
    - name: Run Trivy vulnerability scanner
      uses: aquasecurity/trivy-action@master
      with:
        scan-type: 'fs'
        scan-ref: '.'
        format: 'sarif'
        output: 'trivy-results.sarif'
    
    - name: Upload Trivy scan results
      uses: github/codeql-action/upload-sarif@v2
      with:
        sarif_file: 'trivy-results.sarif'
    
    - name: Scan Docker image
      uses: aquasecurity/trivy-action@master
      with:
        image-ref: 'kindle-sync:test'
        format: 'sarif'
        output: 'trivy-image-results.sarif'
    
    - name: Upload Docker scan results
      uses: github/codeql-action/upload-sarif@v2
      with:
        sarif_file: 'trivy-image-results.sarif'

  # Performance Tests
  performance-tests:
    name: Performance Tests
    runs-on: ubuntu-latest
    needs: integration-tests
    if: github.event_name == 'schedule' || contains(github.event.head_commit.message, '[perf]')
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ env.PYTHON_VERSION }}
        cache: 'pip'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r requirements-test.txt
        pip install pytest-benchmark
    
    - name: Run performance tests
      run: |
        python -m pytest tests/performance/ \
          --benchmark-only \
          --benchmark-save=performance-results \
          --benchmark-save-data
    
    - name: Upload performance results
      uses: actions/upload-artifact@v4
      with:
        name: performance-results
        path: .benchmarks/

  # Build and Push (on main branch)
  build-and-push:
    name: Build and Push
    runs-on: ubuntu-latest
    needs: [docker-build, security-scan]
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v4
    
    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v3
    
    - name: Login to Docker Hub
      uses: docker/login-action@v3
      with:
        username: ${{ secrets.DOCKER_USERNAME }}
        password: ${{ secrets.DOCKER_PASSWORD }}
    
    - name: Extract metadata
      id: meta
      uses: docker/metadata-action@v5
      with:
        images: kindle-sync
        tags: |
          type=ref,event=branch
          type=ref,event=pr
          type=sha,prefix={{branch}}-
          type=raw,value=latest,enable={{is_default_branch}}
    
    - name: Build and push Docker image
      uses: docker/build-push-action@v5
      with:
        context: .
        target: production
        push: true
        tags: ${{ steps.meta.outputs.tags }}
        labels: ${{ steps.meta.outputs.labels }}
        cache-from: type=gha
        cache-to: type=gha,mode=max
        build-args: |
          BUILD_DATE=${{ github.event.head_commit.timestamp }}
          VCS_REF=${{ github.sha }}

  # Deployment (on main branch)
  deploy:
    name: Deploy
    runs-on: ubuntu-latest
    needs: build-and-push
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    environment: production
    
    steps:
    - name: Deploy to production
      run: |
        echo "Deployment would happen here"
        # Add actual deployment steps
```

#### Implementation Steps
1. Create comprehensive CI/CD pipeline
2. Add code quality checks
3. Implement security scanning
4. Add performance testing
5. Set up automated deployment
6. Configure notifications and reporting

#### Benefits
- 🔄 Automated quality assurance
- 🔄 Security vulnerability detection
- 🔄 Performance regression testing
- 🔄 Automated deployment pipeline
- 🔄 Comprehensive reporting

### 12. Monitoring & Observability

#### Current State
```python
# Basic logging
logger.info(f"Processing file: {file_path}")
```

#### Proposed Solution
```python
# src/monitoring/metrics.py
from prometheus_client import Counter, Histogram, Gauge, Info, start_http_server
from typing import Dict, Any
import time

class MetricsCollector:
    """Prometheus metrics collector for Kindle Sync."""
    
    def __init__(self, port: int = 8000):
        self.port = port
        
        # File processing metrics
        self.files_processed = Counter(
            'kindle_sync_files_processed_total',
            'Total number of files processed',
            ['file_type', 'status']
        )
        
        self.file_processing_duration = Histogram(
            'kindle_sync_file_processing_duration_seconds',
            'Time spent processing files',
            ['file_type', 'operation'],
            buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0]
        )
        
        self.active_file_watchers = Gauge(
            'kindle_sync_active_file_watchers',
            'Number of active file watchers'
        )
        
        self.email_send_attempts = Counter(
            'kindle_sync_email_send_attempts_total',
            'Total email send attempts',
            ['status']
        )
        
        self.email_send_duration = Histogram(
            'kindle_sync_email_send_duration_seconds',
            'Time spent sending emails',
            buckets=[1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
        )
        
        self.system_info = Info(
            'kindle_sync_system_info',
            'System information'
        )
        
        self.disk_usage = Gauge(
            'kindle_sync_disk_usage_bytes',
            'Disk usage in bytes',
            ['path']
        )
        
        self.memory_usage = Gauge(
            'kindle_sync_memory_usage_bytes',
            'Memory usage in bytes'
        )
        
        # Set system info
        self.system_info.info({
            'version': '1.0.0',
            'python_version': '3.11',
            'platform': 'raspberry_pi'
        })
    
    def start_server(self):
        """Start Prometheus metrics server."""
        start_http_server(self.port)
        logger.info(f"Metrics server started on port {self.port}")
    
    def record_file_processed(self, file_type: str, status: str):
        """Record file processing."""
        self.files_processed.labels(file_type=file_type, status=status).inc()
    
    def record_processing_time(self, file_type: str, operation: str, duration: float):
        """Record processing time."""
        self.file_processing_duration.labels(
            file_type=file_type, 
            operation=operation
        ).observe(duration)
    
    def record_email_send(self, status: str, duration: float):
        """Record email sending."""
        self.email_send_attempts.labels(status=status).inc()
        self.email_send_duration.observe(duration)
    
    def update_system_metrics(self):
        """Update system metrics."""
        import psutil
        import shutil
        
        # Memory usage
        memory = psutil.virtual_memory()
        self.memory_usage.set(memory.used)
        
        # Disk usage for key paths
        paths = ['/app/data', '/app/logs', '/app/backups']
        for path in paths:
            try:
                if Path(path).exists():
                    usage = shutil.disk_usage(path)
                    self.disk_usage.labels(path=path).set(usage.used)
            except Exception:
                pass

# src/monitoring/structured_logging.py
import structlog
import json
from typing import Any, Dict
from datetime import datetime

def setup_structured_logging(level: str = "INFO"):
    """Set up structured logging with JSON output."""
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Configure standard library logging
    import logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, level.upper()),
    )

class StructuredLogger:
    """Structured logger for Kindle Sync."""
    
    def __init__(self, name: str):
        self.logger = structlog.get_logger(name)
    
    def log_file_processing(self, file_path: str, operation: str, 
                          status: str, duration_ms: float, **kwargs):
        """Log file processing event."""
        self.logger.info(
            "file_processing",
            file_path=file_path,
            operation=operation,
            status=status,
            duration_ms=duration_ms,
            **kwargs
        )
    
    def log_email_send(self, to: str, subject: str, status: str, 
                      duration_ms: float, **kwargs):
        """Log email sending event."""
        self.logger.info(
            "email_send",
            to=to,
            subject=subject,
            status=status,
            duration_ms=duration_ms,
            **kwargs
        )
    
    def log_system_event(self, event_type: str, message: str, **kwargs):
        """Log system event."""
        self.logger.info(
            "system_event",
            event_type=event_type,
            message=message,
            **kwargs
        )
    
    def log_error(self, error_type: str, message: str, **kwargs):
        """Log error event."""
        self.logger.error(
            "error",
            error_type=error_type,
            message=message,
            **kwargs
        )

# src/monitoring/alerting.py
class AlertManager:
    """Alert management system."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.alert_channels = self._setup_alert_channels()
    
    def _setup_alert_channels(self) -> Dict[str, Any]:
        """Set up alert channels."""
        channels = {}
        
        if self.config.get('slack', {}).get('enabled'):
            channels['slack'] = SlackNotifier(self.config['slack'])
        
        if self.config.get('email', {}).get('enabled'):
            channels['email'] = EmailNotifier(self.config['email'])
        
        return channels
    
    def send_alert(self, severity: str, message: str, context: Dict[str, Any]):
        """Send alert to configured channels."""
        for channel_name, channel in self.alert_channels.items():
            try:
                channel.send_alert(severity, message, context)
            except Exception as e:
                logger.error(f"Failed to send alert via {channel_name}: {e}")

class SlackNotifier:
    """Slack notification channel."""
    
    def __init__(self, config: Dict[str, Any]):
        self.webhook_url = config['webhook_url']
        self.channel = config.get('channel', '#kindle-sync')
    
    def send_alert(self, severity: str, message: str, context: Dict[str, Any]):
        """Send alert to Slack."""
        import requests
        
        color = {
            'critical': '#ff0000',
            'warning': '#ffaa00',
            'info': '#00aa00'
        }.get(severity, '#666666')
        
        payload = {
            'channel': self.channel,
            'attachments': [{
                'color': color,
                'title': f'Kindle Sync Alert - {severity.upper()}',
                'text': message,
                'fields': [
                    {'title': k, 'value': str(v), 'short': True}
                    for k, v in context.items()
                ],
                'timestamp': int(time.time())
            }]
        }
        
        response = requests.post(self.webhook_url, json=payload)
        response.raise_for_status()
```

#### Implementation Steps
1. Set up Prometheus metrics collection
2. Implement structured logging
3. Create alert management system
4. Add monitoring dashboard
5. Configure alerting rules
6. Set up log aggregation

#### Benefits
- 📊 Comprehensive metrics collection
- 📊 Structured logging for better analysis
- 📊 Real-time alerting
- 📊 Performance monitoring
- 📊 System health visibility

## Implementation Roadmap

### Phase 1: Foundation (Weeks 1-2)
**Priority: Critical**

#### Week 1: Security & Reliability
- [ ] Implement secrets management system
- [ ] Add comprehensive error handling with retries
- [ ] Create input validation and sanitization
- [ ] Update configuration system with validation
- [ ] Add security scanning to CI/CD

#### Week 2: Core Infrastructure
- [ ] Set up database integration
- [ ] Implement health monitoring system
- [ ] Create structured logging
- [ ] Add metrics collection
- [ ] Update Docker configuration

### Phase 2: Performance & Architecture (Weeks 3-4)
**Priority: High**

#### Week 3: Async Processing
- [ ] Implement async file processing
- [ ] Add thread pool for CPU-bound operations
- [ ] Create async file watcher
- [ ] Update main application loop
- [ ] Add performance monitoring

#### Week 4: Plugin Architecture
- [ ] Create plugin base classes
- [ ] Convert existing processors to plugins
- [ ] Implement plugin manager
- [ ] Add plugin configuration system
- [ ] Create plugin development documentation

### Phase 3: Quality & Operations (Weeks 5-6)
**Priority: Medium**

#### Week 5: Code Quality
- [ ] Add comprehensive type hints
- [ ] Implement code quality checks
- [ ] Create comprehensive test suite
- [ ] Add performance benchmarks
- [ ] Update documentation

#### Week 6: DevOps & Monitoring
- [ ] Enhance CI/CD pipeline
- [ ] Set up monitoring dashboard
- [ ] Configure alerting system
- [ ] Add deployment automation
- [ ] Create operational runbooks

### Phase 4: Advanced Features (Weeks 7-8)
**Priority: Low**

#### Week 7: Advanced Monitoring
- [ ] Implement distributed tracing
- [ ] Add business metrics
- [ ] Create custom dashboards
- [ ] Set up log analysis
- [ ] Add capacity planning tools

#### Week 8: Optimization & Polish
- [ ] Performance optimization
- [ ] Memory usage optimization
- [ ] Add caching layer
- [ ] Implement rate limiting
- [ ] Final testing and validation

## Success Metrics

### Security Metrics
- **Target**: 0 critical security vulnerabilities
- **Measurement**: Automated security scans
- **Frequency**: Every commit and daily

### Reliability Metrics
- **Target**: 99.9% uptime
- **Measurement**: Health check monitoring
- **Frequency**: Continuous

### Performance Metrics
- **Target**: <2 seconds average file processing time
- **Measurement**: Prometheus metrics
- **Frequency**: Continuous

### Quality Metrics
- **Target**: >90% test coverage
- **Measurement**: Code coverage reports
- **Frequency**: Every commit

### Operational Metrics
- **Target**: <5 minutes mean time to recovery
- **Measurement**: Incident tracking
- **Frequency**: Per incident

## Risk Assessment

### High Risk
1. **Breaking Changes**: Major architectural changes may break existing functionality
   - **Mitigation**: Comprehensive testing, gradual rollout, rollback plan
   
2. **Performance Regression**: New features may impact performance
   - **Mitigation**: Performance testing, benchmarking, monitoring

### Medium Risk
1. **Complexity Increase**: New features add complexity
   - **Mitigation**: Good documentation, training, gradual adoption
   
2. **Dependency Management**: New dependencies may introduce vulnerabilities
   - **Mitigation**: Regular security scans, dependency updates

### Low Risk
1. **Learning Curve**: Team needs to learn new technologies
   - **Mitigation**: Training, documentation, mentoring

## Appendices

### Appendix A: Technology Stack

#### Core Technologies
- **Python**: 3.11+
- **Docker**: Multi-stage builds
- **SQLite/PostgreSQL**: State management
- **Prometheus**: Metrics collection
- **Grafana**: Monitoring dashboards

#### Development Tools
- **Pytest**: Testing framework
- **Black**: Code formatting
- **MyPy**: Type checking
- **Bandit**: Security scanning
- **GitHub Actions**: CI/CD

#### Monitoring & Observability
- **Structlog**: Structured logging
- **Prometheus**: Metrics
- **Grafana**: Dashboards
- **AlertManager**: Alerting
- **Jaeger**: Distributed tracing

### Appendix B: Configuration Examples

#### Production Configuration
```yaml
# config.prod.yaml
obsidian:
  vault_path: "/data/obsidian"
  sync_folder: "Kindle Sync"
  watch_subfolders: true

kindle:
  email: "${KINDLE_EMAIL}"
  approved_senders: ["${SMTP_USERNAME}"]

smtp:
  host: "smtp.gmail.com"
  port: 587
  username: "${SMTP_USERNAME}"
  password: "${SMTP_PASSWORD}"
  use_tls: true

processing:
  max_file_size_mb: 50
  concurrent_processing: true
  retry_attempts: 3
  debounce_time: 2.0

logging:
  level: "INFO"
  file: "/app/logs/kindle_sync.log"
  max_size: "10MB"
  backup_count: 5

monitoring:
  metrics_port: 8000
  health_check_interval: 30
  alerting:
    enabled: true
    channels:
      slack:
        enabled: true
        webhook_url: "${SLACK_WEBHOOK_URL}"
        channel: "#kindle-sync"
```

#### Development Configuration
```yaml
# config.dev.yaml
obsidian:
  vault_path: "./test-vault"
  sync_folder: "Kindle Sync"
  watch_subfolders: true

kindle:
  email: "test@kindle.com"
  approved_senders: ["test@gmail.com"]

smtp:
  host: "localhost"
  port: 1025
  username: "test"
  password: "test"
  use_tls: false

processing:
  max_file_size_mb: 10
  concurrent_processing: false
  retry_attempts: 1
  debounce_time: 0.5

logging:
  level: "DEBUG"
  file: "./logs/kindle_sync.log"
  max_size: "1MB"
  backup_count: 2

monitoring:
  metrics_port: 8001
  health_check_interval: 10
  alerting:
    enabled: false
```

### Appendix C: Deployment Checklist

#### Pre-Deployment
- [ ] All tests passing
- [ ] Security scan clean
- [ ] Performance benchmarks met
- [ ] Documentation updated
- [ ] Configuration validated

#### Deployment
- [ ] Backup current system
- [ ] Deploy to staging environment
- [ ] Run integration tests
- [ ] Deploy to production
- [ ] Verify health checks
- [ ] Monitor metrics

#### Post-Deployment
- [ ] Verify all functionality
- [ ] Check error rates
- [ ] Monitor performance
- [ ] Update documentation
- [ ] Notify stakeholders

---

**Document Version**: 1.0  
**Last Updated**: 2024-01-XX  
**Next Review**: 2024-02-XX  
**Owner**: Kindle Sync Development Team
