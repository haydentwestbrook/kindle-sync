"""Health check system for monitoring application status."""

import asyncio
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from loguru import logger
from pathlib import Path

from ..config import Config
from ..database import DatabaseManager


class HealthStatus(str, Enum):
    """Health check status enumeration."""

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"
    ERROR = "error"


@dataclass
class HealthCheckResult:
    """Result of a health check."""

    name: str
    status: HealthStatus
    response_time_ms: Optional[int] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


class HealthChecker:
    """Centralized health check system."""

    def __init__(self, config: Config, db_manager: Optional[DatabaseManager] = None):
        """
        Initialize health checker.

        Args:
            config: Application configuration
            db_manager: Optional database manager for persistence
        """
        self.config = config
        self.db_manager = db_manager
        self.checks: Dict[str, Callable] = {}
        self.check_timeouts: Dict[str, float] = {}

        # Register default health checks
        self._register_default_checks()

        logger.info("Health checker initialized")

    def register_check(self, name: str, check_func: Callable, timeout: float = 5.0):
        """
        Register a health check function.

        Args:
            name: Name of the health check
            check_func: Function that returns HealthCheckResult or raises exception
            timeout: Timeout in seconds for the check
        """
        self.checks[name] = check_func
        self.check_timeouts[name] = timeout
        logger.info(f"Registered health check: {name}")

    def _register_default_checks(self):
        """Register default health checks."""
        # File system check
        self.register_check("filesystem", self._check_filesystem)

        # Configuration check
        self.register_check("configuration", self._check_configuration)

        # Database check
        if self.db_manager:
            self.register_check("database", self._check_database)

        # Memory check
        self.register_check("memory", self._check_memory)

        # Disk space check
        self.register_check("disk_space", self._check_disk_space)

        # Additional checks expected by tests
        self.register_check("config_paths", self._check_config_paths)
        self.register_check("database_connection", self._check_database_connection)
        self.register_check("email_service_config", self._check_email_service_config)
        self.register_check("temp_directory_access", self._check_temp_directory_access)

    async def run_check(self, name: str) -> HealthCheckResult:
        """
        Run a specific health check.

        Args:
            name: Name of the health check to run

        Returns:
            HealthCheckResult with check outcome
        """
        if name not in self.checks:
            return HealthCheckResult(
                name=name,
                status=HealthStatus.UNKNOWN,
                error_message=f"Health check '{name}' not found",
            )

        start_time = time.time()

        try:
            # Run check with timeout
            # Get the method from the instance to allow for proper mocking
            check_method_name = f"_check_{name}"
            if hasattr(self, check_method_name):
                check_func = getattr(self, check_method_name)
            else:
                check_func = self.checks[name]
            
            timeout = self.check_timeouts[name]

            if asyncio.iscoroutinefunction(check_func):
                result = await asyncio.wait_for(check_func(), timeout=timeout)
            else:
                # Run sync function in thread pool
                loop = asyncio.get_event_loop()
                result = await asyncio.wait_for(
                    loop.run_in_executor(None, check_func), timeout=timeout
                )

            response_time = int((time.time() - start_time) * 1000)

            # Ensure result is a HealthCheckResult
            if isinstance(result, HealthCheckResult):
                result.response_time_ms = response_time
            elif isinstance(result, tuple) and len(result) == 2:
                # Convert tuple (status, message) to HealthCheckResult
                status_str, message = result
                status = HealthStatus(status_str) if status_str in [s.value for s in HealthStatus] else HealthStatus.UNHEALTHY
                result = HealthCheckResult(
                    name=name,
                    status=status,
                    response_time_ms=response_time,
                    error_message=message if status != HealthStatus.HEALTHY else None
                )
            else:
                # Convert other types to HealthCheckResult
                result = HealthCheckResult(
                    name=name,
                    status=HealthStatus.HEALTHY if result else HealthStatus.UNHEALTHY,
                    response_time_ms=response_time,
                )

            # Record in database if available
            if self.db_manager:
                self.db_manager.record_health_check(
                    name,
                    result.status.value,
                    result.response_time_ms,
                    result.error_message,
                    result.metadata,
                )

            return result

        except asyncio.TimeoutError:
            response_time = int((time.time() - start_time) * 1000)
            result = HealthCheckResult(
                name=name,
                status=HealthStatus.UNHEALTHY,
                response_time_ms=response_time,
                error_message=f"Health check timed out after {self.check_timeouts[name]}s",
            )

            if self.db_manager:
                self.db_manager.record_health_check(
                    name,
                    result.status.value,
                    result.response_time_ms,
                    result.error_message,
                )

            return result

        except Exception as e:
            response_time = int((time.time() - start_time) * 1000)
            result = HealthCheckResult(
                name=name,
                status=HealthStatus.ERROR,
                response_time_ms=response_time,
                error_message=str(e),
            )

            if self.db_manager:
                self.db_manager.record_health_check(
                    name,
                    result.status.value,
                    result.response_time_ms,
                    result.error_message,
                )

            return result

    async def run_all_checks(self) -> Dict[str, Any]:
        """
        Run all registered health checks.

        Returns:
            Dictionary with overall status and individual check results
        """
        results = {}

        # Run checks concurrently
        tasks = {
            name: asyncio.create_task(self.run_check(name))
            for name in self.checks.keys()
        }

        # Wait for all checks to complete
        for name, task in tasks.items():
            try:
                results[name] = await task
            except Exception as e:
                results[name] = HealthCheckResult(
                    name=name,
                    status=HealthStatus.UNHEALTHY,
                    error_message=f"Check failed: {e}",
                )

        # Determine overall status
        overall_status = self.get_overall_status(results)
        
        return {
            "overall_status": overall_status.value,
            "checks": {
                name: {
                    "status": result.status.value,
                    "message": result.error_message or f"{result.status.value}",
                    "response_time_ms": result.response_time_ms,
                    "metadata": result.metadata
                }
                for name, result in results.items()
            }
        }

    def run_all_checks_sync(self) -> Dict[str, Any]:
        """
        Synchronous version of run_all_checks for testing.
        
        Returns:
            Dictionary with overall status and individual check results
        """
        return asyncio.run(self.run_all_checks())

    def get_overall_status(self, results: Dict[str, HealthCheckResult]) -> HealthStatus:
        """
        Determine overall system health status.

        Args:
            results: Dictionary of health check results

        Returns:
            Overall health status
        """
        if not results:
            return HealthStatus.UNKNOWN

        statuses = [result.status for result in results.values()]

        if HealthStatus.ERROR in statuses:
            return HealthStatus.UNHEALTHY  # Error status makes overall status unhealthy
        elif HealthStatus.UNHEALTHY in statuses:
            return HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED in statuses:
            return HealthStatus.DEGRADED
        elif all(status == HealthStatus.HEALTHY for status in statuses):
            return HealthStatus.HEALTHY
        else:
            return HealthStatus.UNKNOWN

    # Default health check implementations

    def _check_filesystem(self) -> HealthCheckResult:
        """Check file system accessibility."""
        try:
            vault_path = self.config.get_obsidian_vault_path()

            if not vault_path.exists():
                return HealthCheckResult(
                    name="filesystem",
                    status=HealthStatus.UNHEALTHY,
                    error_message=f"Vault path does not exist: {vault_path}",
                )

            if not vault_path.is_dir():
                return HealthCheckResult(
                    name="filesystem",
                    status=HealthStatus.UNHEALTHY,
                    error_message=f"Vault path is not a directory: {vault_path}",
                )

            # Test write access
            test_file = vault_path / ".health_check_test"
            try:
                test_file.write_text("test")
                test_file.unlink()
            except Exception as e:
                return HealthCheckResult(
                    name="filesystem",
                    status=HealthStatus.UNHEALTHY,
                    error_message=f"No write access to vault: {e}",
                )

            return HealthCheckResult(
                name="filesystem",
                status=HealthStatus.HEALTHY,
                metadata={"vault_path": str(vault_path)},
            )

        except Exception as e:
            return HealthCheckResult(
                name="filesystem", status=HealthStatus.UNHEALTHY, error_message=str(e)
            )

    def _check_configuration(self) -> HealthCheckResult:
        """Check configuration validity."""
        try:
            # Validate configuration
            if not self.config.validate():
                return HealthCheckResult(
                    name="configuration",
                    status=HealthStatus.UNHEALTHY,
                    error_message="Configuration validation failed",
                )

            # Check required settings
            required_settings = [
                "obsidian.vault_path",
                "kindle.email",
                "kindle.smtp_server",
                "kindle.smtp_username",
            ]

            missing_settings = []
            for setting in required_settings:
                if not self.config.get(setting):
                    missing_settings.append(setting)

            if missing_settings:
                return HealthCheckResult(
                    name="configuration",
                    status=HealthStatus.UNHEALTHY,
                    error_message=f"Missing required settings: {missing_settings}",
                )

            return HealthCheckResult(
                name="configuration",
                status=HealthStatus.HEALTHY,
                metadata={"required_settings_ok": True},
            )

        except Exception as e:
            return HealthCheckResult(
                name="configuration",
                status=HealthStatus.UNHEALTHY,
                error_message=str(e),
            )

    def _check_database(self) -> HealthCheckResult:
        """Check database connectivity."""
        try:
            if not self.db_manager:
                return HealthCheckResult(
                    name="database",
                    status=HealthStatus.DEGRADED,
                    error_message="Database manager not available",
                )

            # Test database connection
            with self.db_manager.get_session() as session:
                # Simple query to test connection
                session.execute("SELECT 1")

            # Get database info
            db_info = self.db_manager.get_database_info()

            return HealthCheckResult(
                name="database", status=HealthStatus.HEALTHY, metadata=db_info
            )

        except Exception as e:
            return HealthCheckResult(
                name="database", status=HealthStatus.UNHEALTHY, error_message=str(e)
            )

    def _check_memory(self) -> HealthCheckResult:
        """Check memory usage."""
        try:
            import psutil

            # Get memory info
            memory = psutil.virtual_memory()
            memory_percent = memory.percent

            # Determine status based on memory usage
            if memory_percent > 90:
                status = HealthStatus.UNHEALTHY
            elif memory_percent > 80:
                status = HealthStatus.DEGRADED
            else:
                status = HealthStatus.HEALTHY

            return HealthCheckResult(
                name="memory",
                status=status,
                metadata={
                    "memory_percent": memory_percent,
                    "available_mb": memory.available // (1024 * 1024),
                    "total_mb": memory.total // (1024 * 1024),
                },
            )

        except ImportError:
            return HealthCheckResult(
                name="memory",
                status=HealthStatus.DEGRADED,
                error_message="psutil not available for memory monitoring",
            )
        except Exception as e:
            return HealthCheckResult(
                name="memory", status=HealthStatus.UNHEALTHY, error_message=str(e)
            )

    def _check_disk_space(self) -> HealthCheckResult:
        """Check disk space availability."""
        try:
            import shutil

            vault_path = self.config.get_obsidian_vault_path()

            # Get disk usage for the vault path
            total, used, free = shutil.disk_usage(vault_path)
            free_percent = (free / total) * 100

            # Determine status based on free space
            if free_percent < 5:
                status = HealthStatus.UNHEALTHY
            elif free_percent < 10:
                status = HealthStatus.DEGRADED
            else:
                status = HealthStatus.HEALTHY

            return HealthCheckResult(
                name="disk_space",
                status=status,
                metadata={
                    "free_percent": round(free_percent, 2),
                    "free_gb": round(free / (1024**3), 2),
                    "total_gb": round(total / (1024**3), 2),
                    "path": str(vault_path),
                },
            )

        except Exception as e:
            return HealthCheckResult(
                name="disk_space", status=HealthStatus.UNHEALTHY, error_message=str(e)
            )

    # Additional health check methods expected by tests

    def _check_config_paths(self) -> tuple[str, str]:
        """Check configuration paths accessibility."""
        # Get vault path
        vault_path = self.config.get_obsidian_vault_path()
        if not vault_path.exists():
            return ("unhealthy", f"Vault path does not exist: {vault_path}")
        
        if not vault_path.is_dir():
            return ("unhealthy", f"Vault path is not a directory: {vault_path}")
        
        # Check sync folder
        sync_folder = self.config.get_sync_folder_path()
        if not sync_folder.exists():
            try:
                sync_folder.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                return ("unhealthy", f"Sync folder not accessible: {e}")
        
        # Check backup folder
        backup_folder = self.config.get_backup_folder_path()
        try:
            if not backup_folder.exists():
                try:
                    backup_folder.mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    return ("unhealthy", f"Backup folder not creatable: {e}")
        except PermissionError as e:
            return ("unhealthy", f"Backup folder not creatable: {e}")
        
        # Test write access to vault
        test_file = vault_path / ".health_check_test"
        try:
            test_file.write_text("test")
            test_file.unlink()
        except Exception as e:
            return ("unhealthy", f"Vault not readable/writable: {e}")
        
        return ("healthy", "All configured paths are accessible")

    def _check_database_connection(self) -> tuple[str, str]:
        """Check database connection."""
        try:
            if not self.db_manager:
                return ("unhealthy", "Database manager not available")
            
            # Test database connection
            with self.db_manager.get_session() as session:
                # Simple query to test connection
                session.execute("SELECT 1")
            
            return ("healthy", "Database connection successful")
            
        except Exception as e:
            return ("unhealthy", f"Database connection failed: {e}")

    def _check_email_service_config(self) -> tuple[str, str]:
        """Check email service configuration."""
        try:
            # Get SMTP configuration
            smtp_config = self.config.get_smtp_config()
            if not smtp_config.get("server") or not smtp_config.get("username") or not smtp_config.get("password"):
                return ("unhealthy", "Incomplete SMTP configuration")
            
            # Get Kindle email
            kindle_email = self.config.get_kindle_email()
            if not kindle_email:
                return ("unhealthy", "Kindle email address not configured")
            
            return ("healthy", "Email service configuration is complete")
            
        except Exception as e:
            return ("unhealthy", f"Error checking email config: {e}")

    def _check_temp_directory_access(self) -> tuple[str, str]:
        """Check temporary directory access."""
        import tempfile
        import os
        
        # Test temp directory access
        temp_dir = Path(tempfile.gettempdir())
        if not temp_dir.exists():
            return ("unhealthy", "Temporary directory not accessible or writable")
        
        # Check write access using os.access
        try:
            if not os.access(str(temp_dir), os.W_OK):
                return ("unhealthy", "Temporary directory not accessible or writable")
        except OSError as e:
            return ("unhealthy", f"Error accessing temporary directory: {e}")
        
        # Test write access
        test_file = temp_dir / "kindle_sync_health_test"
        try:
            test_file.write_text("test")
            test_file.unlink()
        except Exception as e:
            return ("unhealthy", f"Error accessing temporary directory: {e}")
        
        return ("healthy", "Temporary directory is accessible")
