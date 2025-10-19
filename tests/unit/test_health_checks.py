"""
Unit tests for HealthChecker.

Tests the health check functionality for system components.
"""

import os
import tempfile
from unittest.mock import MagicMock, Mock, patch

import pytest
from pathlib import Path

from src.config import Config
from src.core.exceptions import ErrorSeverity, KindleSyncError
from src.database.manager import DatabaseManager
from src.monitoring.health_checks import HealthChecker


class TestHealthChecker:
    """Test cases for HealthChecker."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration."""
        config = Mock(spec=Config)
        config.get.side_effect = lambda key, default=None: {
            "obsidian.watch_subfolders": True
        }.get(key, default)
        return config

    @pytest.fixture
    def mock_db_manager(self):
        """Create a mock database manager."""
        db_manager = Mock(spec=DatabaseManager)
        return db_manager

    @pytest.fixture
    def health_checker(self, mock_config, mock_db_manager):
        """Create a HealthChecker instance."""
        return HealthChecker(mock_config, mock_db_manager)

    def test_health_checker_initialization(self, mock_config, mock_db_manager):
        """Test HealthChecker initialization."""
        health_checker = HealthChecker(mock_config, mock_db_manager)

        assert health_checker.config == mock_config
        assert health_checker.db_manager == mock_db_manager

    def test_run_all_checks_success(self, health_checker, mock_config, mock_db_manager):
        """Test running all health checks successfully."""
        # Mock all check methods to return healthy status
        with patch.object(
            health_checker,
            "_check_config_paths",
            return_value=("healthy", "All paths accessible"),
        ), patch.object(
            health_checker,
            "_check_database_connection",
            return_value=("healthy", "Database connected"),
        ), patch.object(
            health_checker,
            "_check_email_service_config",
            return_value=("healthy", "Email configured"),
        ), patch.object(
            health_checker,
            "_check_temp_directory_access",
            return_value=("healthy", "Temp directory accessible"),
        ):
            results = health_checker.run_all_checks()

            assert results["overall_status"] == "healthy"
            assert len(results["checks"]) == 4

            for check_name, check_result in results["checks"].items():
                assert check_result["status"] == "healthy"
                assert "message" in check_result

    def test_run_all_checks_with_failures(
        self, health_checker, mock_config, mock_db_manager
    ):
        """Test running all health checks with some failures."""
        # Mock some checks to fail
        with patch.object(
            health_checker,
            "_check_config_paths",
            return_value=("unhealthy", "Paths not accessible"),
        ), patch.object(
            health_checker,
            "_check_database_connection",
            return_value=("healthy", "Database connected"),
        ), patch.object(
            health_checker,
            "_check_email_service_config",
            return_value=("unhealthy", "Email not configured"),
        ), patch.object(
            health_checker,
            "_check_temp_directory_access",
            return_value=("healthy", "Temp directory accessible"),
        ):
            results = health_checker.run_all_checks()

            assert results["overall_status"] == "unhealthy"
            assert results["checks"]["config_paths"]["status"] == "unhealthy"
            assert results["checks"]["database_connection"]["status"] == "healthy"
            assert results["checks"]["email_service_config"]["status"] == "unhealthy"
            assert results["checks"]["temp_directory_access"]["status"] == "healthy"

    def test_run_all_checks_with_exception(
        self, health_checker, mock_config, mock_db_manager
    ):
        """Test running all health checks with an exception."""
        # Mock a check to raise an exception
        with patch.object(
            health_checker,
            "_check_config_paths",
            side_effect=Exception("Test exception"),
        ), patch.object(
            health_checker,
            "_check_database_connection",
            return_value=("healthy", "Database connected"),
        ), patch.object(
            health_checker,
            "_check_email_service_config",
            return_value=("healthy", "Email configured"),
        ), patch.object(
            health_checker,
            "_check_temp_directory_access",
            return_value=("healthy", "Temp directory accessible"),
        ):
            results = health_checker.run_all_checks()

            assert results["overall_status"] == "unhealthy"
            assert results["checks"]["config_paths"]["status"] == "error"
            assert "Test exception" in results["checks"]["config_paths"]["message"]

    def test_check_config_paths_success(self, health_checker, mock_config):
        """Test successful config paths check."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Mock config methods to return existing paths
            mock_config.get_obsidian_vault_path.return_value = temp_path
            mock_config.get_sync_folder_path.return_value = temp_path / "sync"
            mock_config.get_backup_folder_path.return_value = temp_path / "backup"

            # Create the sync folder
            (temp_path / "sync").mkdir()

            status, message = health_checker._check_config_paths()

            assert status == "healthy"
            assert "All configured paths are accessible" in message

    def test_check_config_paths_vault_not_exists(self, health_checker, mock_config):
        """Test config paths check when vault path doesn't exist."""
        mock_config.get_obsidian_vault_path.return_value = Path("/nonexistent/vault")
        mock_config.get_sync_folder_path.return_value = Path("/nonexistent/sync")
        mock_config.get_backup_folder_path.return_value = Path("/nonexistent/backup")

        status, message = health_checker._check_config_paths()

        assert status == "unhealthy"
        assert "does not exist" in message

    def test_check_config_paths_no_permission(self, health_checker, mock_config):
        """Test config paths check when paths have no permission."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create a file instead of directory to simulate permission issue
            test_file = temp_path / "test_file"
            test_file.touch()

            mock_config.get_obsidian_vault_path.return_value = test_file
            mock_config.get_sync_folder_path.return_value = temp_path / "sync"
            mock_config.get_backup_folder_path.return_value = temp_path / "backup"

            status, message = health_checker._check_config_paths()

            assert status == "unhealthy"
            assert "not readable/writable" in message

    def test_check_database_connection_success(self, health_checker, mock_db_manager):
        """Test successful database connection check."""
        # Mock successful database session
        mock_session = Mock()
        mock_db_manager.get_session.return_value.__enter__.return_value = mock_session

        status, message = health_checker._check_database_connection()

        assert status == "healthy"
        assert "Database connection successful" in message

    def test_check_database_connection_failure(self, health_checker, mock_db_manager):
        """Test database connection check failure."""
        # Mock database connection failure
        mock_db_manager.get_session.side_effect = Exception("Connection failed")

        status, message = health_checker._check_database_connection()

        assert status == "unhealthy"
        assert "Database connection failed" in message

    def test_check_email_service_config_success(self, health_checker, mock_config):
        """Test successful email service config check."""
        # Mock complete email configuration
        mock_config.get_smtp_config.return_value = {
            "server": "smtp.gmail.com",
            "username": "test@example.com",
            "password": "password123",
        }
        mock_config.get_kindle_email.return_value = "kindle@example.com"

        status, message = health_checker._check_email_service_config()

        assert status == "healthy"
        assert "Email service configuration is complete" in message

    def test_check_email_service_config_incomplete_smtp(
        self, health_checker, mock_config
    ):
        """Test email service config check with incomplete SMTP config."""
        # Mock incomplete SMTP configuration
        mock_config.get_smtp_config.return_value = {
            "server": "smtp.gmail.com",
            "username": "test@example.com",
            "password": "",  # Missing password
        }
        mock_config.get_kindle_email.return_value = "kindle@example.com"

        status, message = health_checker._check_email_service_config()

        assert status == "unhealthy"
        assert "Incomplete SMTP configuration" in message

    def test_check_email_service_config_missing_kindle_email(
        self, health_checker, mock_config
    ):
        """Test email service config check with missing Kindle email."""
        # Mock complete SMTP but missing Kindle email
        mock_config.get_smtp_config.return_value = {
            "server": "smtp.gmail.com",
            "username": "test@example.com",
            "password": "password123",
        }
        mock_config.get_kindle_email.return_value = ""

        status, message = health_checker._check_email_service_config()

        assert status == "unhealthy"
        assert "Kindle email address not configured" in message

    def test_check_temp_directory_access_success(self, health_checker):
        """Test successful temp directory access check."""
        with patch("os.access", return_value=True), patch(
            "pathlib.Path.exists", return_value=True
        ), patch("pathlib.Path.write_text"), patch("pathlib.Path.unlink"):
            status, message = health_checker._check_temp_directory_access()

            assert status == "healthy"
            assert "Temporary directory is accessible" in message

    def test_check_temp_directory_access_not_accessible(self, health_checker):
        """Test temp directory access check when not accessible."""
        with patch("os.access", return_value=False), patch(
            "pathlib.Path.exists", return_value=True
        ):
            status, message = health_checker._check_temp_directory_access()

            assert status == "unhealthy"
            assert "not accessible or writable" in message

    def test_check_temp_directory_access_error(self, health_checker):
        """Test temp directory access check with error."""
        with patch("os.access", side_effect=OSError("Permission denied")):
            status, message = health_checker._check_temp_directory_access()

            assert status == "unhealthy"
            assert "Error accessing temporary directory" in message

    def test_check_temp_directory_access_file_creation_error(self, health_checker):
        """Test temp directory access check with file creation error."""
        with patch("os.access", return_value=True), patch(
            "pathlib.Path.exists", return_value=True
        ), patch("pathlib.Path.write_text", side_effect=OSError("Write failed")):
            status, message = health_checker._check_temp_directory_access()

            assert status == "unhealthy"
            assert "Error accessing temporary directory" in message

    def test_check_config_paths_backup_folder_creation(
        self, health_checker, mock_config
    ):
        """Test config paths check with backup folder creation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Mock config methods
            mock_config.get_obsidian_vault_path.return_value = temp_path
            mock_config.get_sync_folder_path.return_value = temp_path / "sync"
            mock_config.get_backup_folder_path.return_value = temp_path / "backup"

            # Create the sync folder
            (temp_path / "sync").mkdir()

            # Backup folder doesn't exist initially
            assert not (temp_path / "backup").exists()

            status, message = health_checker._check_config_paths()

            assert status == "healthy"
            # Backup folder should be created and then removed during the test
            assert "All configured paths are accessible" in message

    def test_check_config_paths_backup_folder_creation_failure(
        self, health_checker, mock_config
    ):
        """Test config paths check with backup folder creation failure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Mock config methods
            mock_config.get_obsidian_vault_path.return_value = temp_path
            mock_config.get_sync_folder_path.return_value = temp_path / "sync"
            mock_config.get_backup_folder_path.return_value = Path(
                "/root/backup"
            )  # Unwritable path

            # Create the sync folder
            (temp_path / "sync").mkdir()

            status, message = health_checker._check_config_paths()

            assert status == "unhealthy"
            assert "not creatable" in message
