"""Unit tests for configuration management."""

from unittest.mock import patch

import pytest
import yaml
from pathlib import Path

from src.config import Config
from src.core.exceptions import ConfigurationError


class TestConfig:
    """Test cases for Config class."""

    def test_config_initialization(self, config_file: Path, sample_config: dict):
        """Test Config initialization with valid file."""
        config = Config(str(config_file))
        assert config.config_path == config_file

        # The Config class expands relative paths, so we need to check the
        # expanded version
        expected_config = sample_config.copy()
        expected_config["sync"]["backup_folder"] = str(Path.cwd() / "Backups")
        assert config._raw_config == expected_config

    def test_config_file_not_found(self, temp_dir: Path):
        """Test Config initialization with non-existent file."""
        non_existent_file = temp_dir / "non_existent.yaml"

        with pytest.raises(ConfigurationError):
            Config(str(non_existent_file))

    def test_config_invalid_yaml(self, temp_dir: Path):
        """Test Config initialization with invalid YAML."""
        invalid_yaml_file = temp_dir / "invalid.yaml"
        invalid_yaml_file.write_text("invalid: yaml: content: [")

        with pytest.raises(ConfigurationError):
            Config(str(invalid_yaml_file))

    def test_get_method(self, config: Config, obsidian_vault: Path):
        """Test get method for configuration values."""
        # Test existing key
        assert config.get("obsidian.vault_path") == str(obsidian_vault)
        assert config.get("kindle.email") == "test@kindle.com"

        # Test non-existing key with default
        assert config.get("non.existing.key", "default_value") == "default_value"

        # Test non-existing key without default
        assert config.get("non.existing.key") is None

    def test_get_obsidian_vault_path(self, config: Config, obsidian_vault: Path):
        """Test get_obsidian_vault_path method."""
        vault_path = config.get_obsidian_vault_path()
        assert vault_path == obsidian_vault

    def test_get_sync_folder_path(self, config: Config, obsidian_vault: Path):
        """Test get_sync_folder_path method."""
        sync_path = config.get_sync_folder_path()
        expected = obsidian_vault / "Kindle Sync"
        assert sync_path == expected

    def test_get_templates_folder_path(self, config: Config, obsidian_vault: Path):
        """Test get_templates_folder_path method."""
        templates_path = config.get_templates_folder_path()
        expected = obsidian_vault / "Templates"
        assert templates_path == expected

    def test_get_backup_folder_path(self, config: Config):
        """Test get_backup_folder_path method."""
        backup_path = config.get_backup_folder_path()
        assert backup_path == Path.cwd() / "Backups"

    def test_get_kindle_email(self, config: Config):
        """Test get_kindle_email method."""
        email = config.get_kindle_email()
        assert email == "test@kindle.com"

    def test_get_approved_senders(self, config: Config):
        """Test get_approved_senders method."""
        senders = config.get_approved_senders()
        assert senders == ["test@example.com"]

    def test_get_smtp_config(self, config: Config):
        """Test get_smtp_config method."""
        smtp_config = config.get_smtp_config()
        expected = {
            "server": "smtp.gmail.com",
            "port": 587,
            "username": "test@gmail.com",
            "password": "test_password",
        }
        assert smtp_config == expected

    def test_get_ocr_config(self, config: Config):
        """Test get_ocr_config method."""
        ocr_config = config.get_ocr_config()
        expected = {"language": "eng", "confidence_threshold": 60}
        assert ocr_config == expected

    def test_get_pdf_config(self, config: Config):
        """Test get_pdf_config method."""
        pdf_config = config.get_pdf_config()
        expected = {
            "page_size": "A4",
            "margins": [72, 72, 72, 72],
            "font_family": "Times-Roman",
            "font_size": 12,
            "line_spacing": 1.2,
        }
        assert pdf_config == expected

    def test_get_markdown_config(self, config: Config):
        """Test get_markdown_config method."""
        markdown_config = config.get_markdown_config()
        expected = {
            "extensions": ["tables", "fenced_code", "toc"],
            "preserve_links": True,
        }
        assert markdown_config == expected

    def test_get_sync_config(self, config: Config):
        """Test get_sync_config method."""
        sync_config = config.get_sync_config()
        expected = {
            "auto_convert_on_save": True,
            "auto_send_to_kindle": True,
            "backup_originals": True,
            "backup_folder": str(Path.cwd() / "Backups"),
        }
        assert sync_config == expected

    def test_get_patterns(self, config: Config):
        """Test get_patterns method."""
        patterns = config.get_patterns()
        expected = {
            "markdown_files": "*.md",
            "pdf_files": "*.pdf",
            "image_files": "*.{png,jpg,jpeg}",
        }
        assert patterns == expected

    def test_get_logging_config(self, config: Config):
        """Test get_logging_config method."""
        logging_config = config.get_logging_config()
        expected = {
            "level": "DEBUG",
            "file": "test.log",
            "max_size": "1MB",
            "backup_count": 2,
        }
        assert logging_config == expected

    def test_get_advanced_config(self, config: Config):
        """Test get_advanced_config method."""
        advanced_config = config.get_advanced_config()
        expected = {
            "debounce_time": 0.1,
            "max_file_size": "10MB",
            "concurrent_processing": False,
            "retry_attempts": 1,
        }
        assert advanced_config == expected

    def test_path_expansion(self, temp_dir: Path):
        """Test path expansion functionality."""
        config_data = {
            "obsidian": {"vault_path": "~/test_vault"},
            "sync": {"backup_folder": "~/backups"},
            "kindle": {"email": "test@kindle.com"},
            "smtp": {
                "host": "smtp.gmail.com",
                "port": 587,
                "username": "test@gmail.com",
                "password": "test_password"
            }
        }

        config_file = temp_dir / "test_config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        with patch("pathlib.Path.expanduser") as mock_expand, patch(
            "src.config.SecretsManager"
        ) as mock_secrets_class:
            # Create the test directory
            test_vault_path = temp_dir / "test_vault"
            test_vault_path.mkdir()
            
            mock_expand.return_value = test_vault_path
            mock_secrets_instance = mock_secrets_class.return_value
            mock_secrets_instance.get_secret.return_value = None

            config = Config(str(config_file))

            # Verify expanduser was called
            mock_expand.assert_called()

    def test_validate_success(self, config: Config, obsidian_vault: Path):
        """Test successful configuration validation."""
        # Mock the vault path to exist
        with patch.object(
            config, "get_obsidian_vault_path", return_value=obsidian_vault
        ):
            assert config.validate() is True

    def test_validate_missing_vault_path(self, config: Config):
        """Test validation failure with missing vault path."""
        with patch.object(
            config, "get_obsidian_vault_path", return_value=Path("/non/existent/path")
        ):
            assert config.validate() is False

    def test_validate_invalid_email(self, config: Config, obsidian_vault: Path):
        """Test validation failure with invalid email."""
        with patch.object(
            config, "get_obsidian_vault_path", return_value=obsidian_vault
        ):
            with patch.object(config, "get_kindle_email", return_value=""):
                assert config.validate() is False

    def test_validate_missing_smtp_config(self, config: Config, obsidian_vault: Path):
        """Test validation failure with missing SMTP config."""
        with patch.object(
            config, "get_obsidian_vault_path", return_value=obsidian_vault
        ):
            with patch.object(
                config,
                "get_smtp_config",
                return_value={"server": "", "username": "", "password": ""},
            ):
                assert config.validate() is False

    def test_config_with_empty_values(self, temp_dir: Path):
        """Test Config with empty configuration values."""
        empty_config = {}
        config_file = temp_dir / "empty_config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(empty_config, f)

        config = Config(str(config_file))

        # Test that methods return defaults for empty config
        assert config.get_obsidian_vault_path() == Path("")
        assert config.get_kindle_email() == ""
        assert config.get_approved_senders() == []
        assert config.get_smtp_config() == {
            "server": "",
            "port": 587,
            "username": "",
            "password": "",
        }

    def test_nested_key_access(self, config: Config):
        """Test accessing deeply nested configuration keys."""
        # Test valid nested key
        assert config.get("processing.pdf.page_size") == "A4"

        # Test invalid nested key
        assert config.get("processing.pdf.non_existing") is None

        # Test partial path
        assert config.get("processing.pdf") == {
            "page_size": "A4",
            "margins": [72, 72, 72, 72],
            "font_family": "Times-Roman",
            "font_size": 12,
            "line_spacing": 1.2,
        }
