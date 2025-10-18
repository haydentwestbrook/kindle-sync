"""Configuration management for the Kindle Scribe sync system."""

from pathlib import Path
from typing import Any, Dict, List, Optional
import os

import yaml
from loguru import logger

from .core.exceptions import ConfigurationError, ErrorSeverity
from .security.secrets_manager import SecretsManager

# Try to import pydantic, fallback to basic validation if not available
try:
    from pydantic import BaseModel, Field, validator
except ImportError:
    # Fallback to basic class if pydantic is not available
    class BaseModel:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)
    
    def validator(field_name):
        def decorator(func):
            return func
        return decorator
    
    def Field(default=None, **kwargs):
        return default


class ObsidianConfig(BaseModel):
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


class KindleConfig(BaseModel):
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


class SMTPConfig(BaseModel):
    """SMTP configuration schema."""
    host: str = Field(..., description="SMTP server host")
    port: int = Field(default=587, ge=1, le=65535, description="SMTP server port")
    username: str = Field(..., description="SMTP username")
    password: str = Field(..., description="SMTP password")
    use_tls: bool = Field(default=True, description="Use TLS encryption")


class ProcessingConfig(BaseModel):
    """File processing configuration schema."""
    max_file_size_mb: int = Field(default=50, ge=1, le=500, description="Maximum file size in MB")
    concurrent_processing: bool = Field(default=True, description="Enable concurrent processing")
    retry_attempts: int = Field(default=3, ge=1, le=10, description="Number of retry attempts")
    debounce_time: float = Field(default=2.0, ge=0.1, le=10.0, description="File change debounce time")


class LoggingConfig(BaseModel):
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


class KindleSyncConfig(BaseModel):
    """Main configuration schema."""
    obsidian: ObsidianConfig
    kindle: KindleConfig
    smtp: SMTPConfig
    processing: ProcessingConfig = Field(default_factory=ProcessingConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    
    # Advanced settings
    advanced: Dict[str, Any] = Field(default_factory=dict)


class Config:
    """Configuration manager for the sync system."""

    def __init__(self, config_path: str = "config.yaml"):
        """Initialize configuration from YAML file."""
        self.config_path = Path(config_path)
        self._raw_config = self._load_config()
        self._expand_paths()
        self._secrets_manager = SecretsManager(config=self._raw_config)
        self._config = self._validate_and_parse_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        if not self.config_path.exists():
            raise ConfigurationError(
                f"Configuration file not found: {self.config_path}",
                config_key="config_path",
                severity=ErrorSeverity.CRITICAL
            )

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
            logger.info(f"Configuration loaded from {self.config_path}")
            return config or {}
        except yaml.YAMLError as e:
            raise ConfigurationError(
                f"Error parsing configuration file: {e}",
                config_key="yaml_parsing",
                severity=ErrorSeverity.CRITICAL
            )
        except Exception as e:
            raise ConfigurationError(
                f"Error loading configuration: {e}",
                config_key="file_loading",
                severity=ErrorSeverity.CRITICAL
            )

    def _expand_paths(self):
        """Expand relative paths to absolute paths."""
        # Expand Obsidian vault path
        if "obsidian" in self._raw_config:
            vault_path = self._raw_config["obsidian"].get("vault_path", "")
            if vault_path:
                self._raw_config["obsidian"]["vault_path"] = str(
                    Path(vault_path).expanduser().resolve()
                )

        # Expand backup folder path
        if "sync" in self._raw_config and "backup_folder" in self._raw_config["sync"]:
            backup_folder = self._raw_config["sync"]["backup_folder"]
            if backup_folder:
                self._raw_config["sync"]["backup_folder"] = str(
                    Path(backup_folder).expanduser().resolve()
                )
    
    def _validate_and_parse_config(self) -> KindleSyncConfig:
        """Validate and parse configuration using Pydantic models."""
        try:
            # Handle environment variable overrides
            self._apply_env_overrides()
            
            # Parse with Pydantic
            config = KindleSyncConfig(**self._raw_config)
            logger.info("Configuration validation successful")
            return config
        except Exception as e:
            raise ConfigurationError(
                f"Configuration validation failed: {e}",
                config_key="validation",
                severity=ErrorSeverity.CRITICAL
            )
    
    def _apply_env_overrides(self):
        """Apply environment variable overrides to configuration."""
        env_mappings = {
            'OBSIDIAN_VAULT_PATH': 'obsidian.vault_path',
            'KINDLE_EMAIL': 'kindle.email',
            'SMTP_HOST': 'smtp.host',
            'SMTP_PORT': 'smtp.port',
            'SMTP_USERNAME': 'smtp.username',
            'SMTP_PASSWORD': 'smtp.password',
            'LOG_LEVEL': 'logging.level',
        }
        
        for env_var, config_path in env_mappings.items():
            env_value = os.getenv(env_var)
            if env_value:
                self._set_nested_value(self._raw_config, config_path, env_value)
                logger.debug(f"Applied environment override: {env_var} -> {config_path}")
    
    def _set_nested_value(self, data: Dict[str, Any], key: str, value: Any) -> None:
        """Set nested value using dot notation."""
        keys = key.split('.')
        config = data
        
        # Navigate to parent, creating intermediate dicts as needed
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        # Set the value
        config[keys[-1]] = value

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by dot-separated key."""
        try:
            # Try to get from the raw config first (for backward compatibility)
            return self._get_nested_value(self._raw_config, key)
        except (KeyError, TypeError):
            return default
    
    def _get_nested_value(self, data: Dict[str, Any], key: str) -> Any:
        """Get nested value using dot notation."""
        keys = key.split('.')
        value = data
        
        for k in keys:
            if not isinstance(value, dict) or k not in value:
                raise KeyError(f"Key '{key}' not found")
            value = value[k]
        
        return value

    def get_obsidian_vault_path(self) -> Path:
        """Get the Obsidian vault path."""
        return Path(self.get("obsidian.vault_path", ""))

    def get_sync_folder_path(self) -> Path:
        """Get the sync folder path within the vault."""
        vault_path = self.get_obsidian_vault_path()
        sync_folder = self.get("obsidian.sync_folder", "Kindle Sync")
        return vault_path / sync_folder

    def get_templates_folder_path(self) -> Path:
        """Get the templates folder path within the vault."""
        vault_path = self.get_obsidian_vault_path()
        templates_folder = self.get("obsidian.templates_folder", "Templates")
        return vault_path / templates_folder

    def get_backup_folder_path(self) -> Path:
        """Get the backup folder path."""
        return Path(self.get("sync.backup_folder", "Backups"))

    def get_kindle_email(self) -> str:
        """Get the Kindle email address."""
        return self.get("kindle.email", "")

    def get_approved_senders(self) -> List[str]:
        """Get the list of approved email senders."""
        return self.get("kindle.approved_senders", [])

    def get_smtp_config(self) -> Dict[str, Any]:
        """Get SMTP configuration with secrets management."""
        return {
            "server": self.get("kindle.smtp_server", ""),
            "port": self.get("kindle.smtp_port", 587),
            "username": self.get("kindle.smtp_username", ""),
            "password": self._get_smtp_password(),
        }
    
    def _get_smtp_password(self) -> str:
        """Get SMTP password from secrets manager."""
        # Try to get from secrets manager first
        password = self._secrets_manager.get_secret("smtp_password")
        if password:
            return password
        
        # Fallback to direct config (for backward compatibility)
        return self.get("kindle.smtp_password", "")

    def get_imap_config(self) -> Dict[str, Any]:
        """Get IMAP configuration for email receiving."""
        return {
            "server": self.get("email_receiving.imap_server", ""),
            "port": self.get("email_receiving.imap_port", 993),
            "username": self.get("email_receiving.username", ""),
            "password": self.get("email_receiving.password", ""),
            "check_interval": self.get("email_receiving.check_interval", 300),
            "max_emails": self.get("email_receiving.max_emails_per_check", 10),
            "mark_as_read": self.get("email_receiving.mark_as_read", True),
            "delete_after": self.get("email_receiving.delete_after_processing", False),
        }

    def get_ocr_config(self) -> Dict[str, Any]:
        """Get OCR configuration."""
        return self.get("processing.ocr", {})

    def get_pdf_config(self) -> Dict[str, Any]:
        """Get PDF generation configuration."""
        return self.get("processing.pdf", {})

    def get_markdown_config(self) -> Dict[str, Any]:
        """Get Markdown processing configuration."""
        return self.get("processing.markdown", {})

    def get_sync_config(self) -> Dict[str, Any]:
        """Get sync configuration."""
        return self.get("sync", {})

    def get_patterns(self) -> Dict[str, str]:
        """Get file patterns."""
        return self.get("patterns", {})

    def get_logging_config(self) -> Dict[str, Any]:
        """Get logging configuration."""
        return self.get("logging", {})

    def get_advanced_config(self) -> Dict[str, Any]:
        """Get advanced configuration."""
        return self.get("advanced", {})

    def validate(self) -> bool:
        """Validate configuration."""
        try:
            # The configuration is already validated during initialization
            # This method provides additional runtime validation
            
            # Check required paths
            vault_path = self.get_obsidian_vault_path()
            if not vault_path.exists():
                raise ConfigurationError(
                    f"Obsidian vault path does not exist: {vault_path}",
                    config_key="obsidian.vault_path",
                    severity=ErrorSeverity.HIGH
                )

            # Check Kindle email
            kindle_email = self.get_kindle_email()
            if not kindle_email:
                raise ConfigurationError(
                    "Valid Kindle email address is required",
                    config_key="kindle.email",
                    severity=ErrorSeverity.HIGH
                )

            # Check SMTP configuration
            smtp_config = self.get_smtp_config()
            if not all([smtp_config["server"], smtp_config["username"], smtp_config["password"]]):
                raise ConfigurationError(
                    "Complete SMTP configuration is required",
                    config_key="smtp",
                    severity=ErrorSeverity.HIGH
                )

            logger.info("Configuration validation passed")
            return True
            
        except ConfigurationError as e:
            logger.error(f"Configuration validation error: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected configuration validation error: {e}")
            return False
    
    def get_secrets_manager(self) -> SecretsManager:
        """Get the secrets manager instance."""
        return self._secrets_manager
    
    def migrate_secrets(self) -> bool:
        """Migrate plaintext secrets to encrypted storage."""
        try:
            migrated_config = self._secrets_manager.migrate_plaintext_secrets(self._raw_config)
            
            # Update the raw config
            self._raw_config = migrated_config
            
            # Re-parse the configuration
            self._config = self._validate_and_parse_config()
            
            logger.info("Secrets migration completed successfully")
            return True
        except Exception as e:
            logger.error(f"Secrets migration failed: {e}")
            return False
