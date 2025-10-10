"""Configuration management for the Kindle Scribe sync system."""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, List
from loguru import logger


class Config:
    """Configuration manager for the sync system."""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize configuration from YAML file."""
        self.config_path = Path(config_path)
        self._config = self._load_config()
        self._expand_paths()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        if not self.config_path.exists():
            logger.error(f"Configuration file not found: {self.config_path}")
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            logger.info(f"Configuration loaded from {self.config_path}")
            return config
        except yaml.YAMLError as e:
            logger.error(f"Error parsing configuration file: {e}")
            raise
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            raise
    
    def _expand_paths(self):
        """Expand relative paths to absolute paths."""
        # Expand Obsidian vault path
        if 'obsidian' in self._config:
            vault_path = self._config['obsidian'].get('vault_path', '')
            if vault_path:
                self._config['obsidian']['vault_path'] = str(Path(vault_path).expanduser().resolve())
        
        # Expand backup folder path
        if 'sync' in self._config and 'backup_folder' in self._config['sync']:
            backup_folder = self._config['sync']['backup_folder']
            if backup_folder:
                self._config['sync']['backup_folder'] = str(Path(backup_folder).expanduser().resolve())
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by dot-separated key."""
        keys = key.split('.')
        value = self._config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def get_obsidian_vault_path(self) -> Path:
        """Get the Obsidian vault path."""
        return Path(self.get('obsidian.vault_path', ''))
    
    def get_sync_folder_path(self) -> Path:
        """Get the sync folder path within the vault."""
        vault_path = self.get_obsidian_vault_path()
        sync_folder = self.get('obsidian.sync_folder', 'Kindle Sync')
        return vault_path / sync_folder
    
    def get_templates_folder_path(self) -> Path:
        """Get the templates folder path within the vault."""
        vault_path = self.get_obsidian_vault_path()
        templates_folder = self.get('obsidian.templates_folder', 'Templates')
        return vault_path / templates_folder
    
    def get_backup_folder_path(self) -> Path:
        """Get the backup folder path."""
        return Path(self.get('sync.backup_folder', 'Backups'))
    
    def get_kindle_email(self) -> str:
        """Get the Kindle email address."""
        return self.get('kindle.email', '')
    
    def get_approved_senders(self) -> List[str]:
        """Get the list of approved email senders."""
        return self.get('kindle.approved_senders', [])
    
    def get_smtp_config(self) -> Dict[str, Any]:
        """Get SMTP configuration."""
        return {
            'server': self.get('kindle.smtp_server', ''),
            'port': self.get('kindle.smtp_port', 587),
            'username': self.get('kindle.smtp_username', ''),
            'password': self.get('kindle.smtp_password', '')
        }
    
    def get_ocr_config(self) -> Dict[str, Any]:
        """Get OCR configuration."""
        return self.get('processing.ocr', {})
    
    def get_pdf_config(self) -> Dict[str, Any]:
        """Get PDF generation configuration."""
        return self.get('processing.pdf', {})
    
    def get_markdown_config(self) -> Dict[str, Any]:
        """Get Markdown processing configuration."""
        return self.get('processing.markdown', {})
    
    def get_sync_config(self) -> Dict[str, Any]:
        """Get sync configuration."""
        return self.get('sync', {})
    
    def get_patterns(self) -> Dict[str, str]:
        """Get file patterns."""
        return self.get('patterns', {})
    
    def get_logging_config(self) -> Dict[str, Any]:
        """Get logging configuration."""
        return self.get('logging', {})
    
    def get_advanced_config(self) -> Dict[str, Any]:
        """Get advanced configuration."""
        return self.get('advanced', {})
    
    def validate(self) -> bool:
        """Validate configuration."""
        errors = []
        
        # Check required paths
        vault_path = self.get_obsidian_vault_path()
        if not vault_path.exists():
            errors.append(f"Obsidian vault path does not exist: {vault_path}")
        
        # Check Kindle email
        kindle_email = self.get_kindle_email()
        if not kindle_email or '@' not in kindle_email:
            errors.append("Valid Kindle email address is required")
        
        # Check SMTP configuration
        smtp_config = self.get_smtp_config()
        if not all([smtp_config['server'], smtp_config['username'], smtp_config['password']]):
            errors.append("Complete SMTP configuration is required")
        
        if errors:
            for error in errors:
                logger.error(f"Configuration validation error: {error}")
            return False
        
        logger.info("Configuration validation passed")
        return True
