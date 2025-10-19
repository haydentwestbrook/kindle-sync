"""Secure secrets management with encryption at rest."""

import base64
import os
from typing import Any, Dict, Optional

from cryptography.fernet import Fernet
from loguru import logger
from pathlib import Path

from ..core.exceptions import ErrorSeverity, SecretsError


class SecretsManager:
    """Secure secrets management with encryption at rest."""

    def __init__(
        self, key_path: Optional[Path] = None, config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize secrets manager.

        Args:
            key_path: Path to encryption key file
            config: Configuration dictionary for accessing secrets
        """
        self.config = config if config is not None else {}
        self.key_path = key_path or Path.home() / ".kindle-sync" / "secrets.key"
        self._ensure_key_exists()
        self.cipher = Fernet(self._load_key())

        logger.info(f"Secrets manager initialized with key at: {self.key_path}")

    def _ensure_key_exists(self) -> None:
        """Generate encryption key if it doesn't exist."""
        if not self.key_path.exists():
            try:
                self.key_path.parent.mkdir(parents=True, exist_ok=True)
                key = Fernet.generate_key()
                self.key_path.write_bytes(key)
                self.key_path.chmod(0o600)  # Owner read/write only
                logger.info(f"Generated new encryption key at: {self.key_path}")
            except Exception as e:
                raise SecretsError(
                    f"Failed to create encryption key: {e}",
                    severity=ErrorSeverity.CRITICAL,
                )

    def _load_key(self) -> bytes:
        """Load encryption key from file."""
        try:
            return self.key_path.read_bytes()
        except Exception as e:
            raise SecretsError(
                f"Failed to load encryption key: {e}", severity=ErrorSeverity.CRITICAL
            )

    def encrypt_secret(self, secret: str) -> str:
        """
        Encrypt a secret value.

        Args:
            secret: Plain text secret to encrypt

        Returns:
            Base64 encoded encrypted secret
        """
        try:
            encrypted_bytes = self.cipher.encrypt(secret.encode("utf-8"))
            return base64.b64encode(encrypted_bytes).decode("utf-8")
        except Exception as e:
            raise SecretsError(
                f"Failed to encrypt secret: {e}", severity=ErrorSeverity.HIGH
            )

    def decrypt_secret(self, encrypted_secret: str) -> str:
        """
        Decrypt a secret value.

        Args:
            encrypted_secret: Base64 encoded encrypted secret

        Returns:
            Decrypted plain text secret
        """
        try:
            encrypted_bytes = base64.b64decode(encrypted_secret.encode("utf-8"))
            decrypted_bytes = self.cipher.decrypt(encrypted_bytes)
            return decrypted_bytes.decode("utf-8")
        except Exception as e:
            raise SecretsError(
                f"Failed to decrypt secret: {e}", severity=ErrorSeverity.HIGH
            )

    def get_secret(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        Get secret from environment or encrypted storage.

        Priority order:
        1. Environment variable
        2. Encrypted config value
        3. Default value

        Args:
            key: Secret key name
            default: Default value if secret not found

        Returns:
            Secret value or default
        """
        # Priority 1: Environment variable
        env_key = f"KINDLE_SYNC_{key.upper()}"
        env_value = os.getenv(env_key)
        if env_value:
            logger.debug(f"Retrieved secret '{key}' from environment variable")
            return env_value

        # Priority 2: Encrypted config value
        try:
            encrypted_value = self._get_config_value(f"secrets.{key}")
            if encrypted_value:
                decrypted_value = self.decrypt_secret(encrypted_value)
                logger.debug(f"Retrieved secret '{key}' from encrypted config")
                return decrypted_value
        except Exception as e:
            logger.warning(f"Failed to decrypt secret '{key}': {e}")

        # Priority 3: Default value
        if default is not None:
            logger.debug(f"Using default value for secret '{key}'")
            return default

        logger.warning(f"Secret '{key}' not found in any source")
        return None

    def set_secret(self, key: str, value: str, encrypt: bool = True) -> None:
        """
        Set a secret value.

        Args:
            key: Secret key name
            value: Secret value
            encrypt: Whether to encrypt the value before storage
        """
        try:
            if encrypt:
                encrypted_value = self.encrypt_secret(value)
                self._set_config_value(f"secrets.{key}", encrypted_value)
                logger.info(f"Encrypted and stored secret '{key}'")
            else:
                self._set_config_value(f"secrets.{key}", value)
                logger.info(f"Stored secret '{key}' (unencrypted)")
        except Exception as e:
            raise SecretsError(
                f"Failed to set secret '{key}': {e}",
                secret_key=key,
                severity=ErrorSeverity.HIGH,
            )

    def delete_secret(self, key: str) -> bool:
        """
        Delete a secret.

        Args:
            key: Secret key name

        Returns:
            True if secret was deleted, False if not found
        """
        try:
            config_key = f"secrets.{key}"
            if self._has_config_value(config_key):
                self._remove_config_value(config_key)
                logger.info(f"Deleted secret '{key}'")
                return True
            else:
                logger.warning(f"Secret '{key}' not found for deletion")
                return False
        except Exception as e:
            raise SecretsError(
                f"Failed to delete secret '{key}': {e}",
                secret_key=key,
                severity=ErrorSeverity.MEDIUM,
            )

    def list_secrets(self) -> list[str]:
        """
        List all available secret keys.

        Returns:
            List of secret key names
        """
        try:
            secrets_section = self._get_config_value("secrets")
            if isinstance(secrets_section, dict):
                return list(secrets_section.keys())
            return []
        except Exception as e:
            logger.warning(f"Failed to list secrets: {e}")
            return []

    def migrate_plaintext_secrets(
        self, plaintext_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Migrate plaintext secrets to encrypted storage.

        Args:
            plaintext_config: Configuration with plaintext secrets

        Returns:
            Updated configuration with encrypted secrets
        """
        migrated_config = plaintext_config.copy()
        secrets_to_migrate = [
            "kindle.smtp_password",
            "email.smtp.password",
            "email_receiving.password",
        ]

        for config_key in secrets_to_migrate:
            try:
                value = self._get_nested_value(plaintext_config, config_key)
                if (
                    value
                    and isinstance(value, str)
                    and not value.startswith("encrypted:")
                ):
                    # Encrypt the secret
                    encrypted_value = self.encrypt_secret(value)
                    self._set_nested_value(
                        migrated_config, config_key, f"encrypted:{encrypted_value}"
                    )
                    logger.info(f"Migrated secret '{config_key}' to encrypted storage")
            except Exception as e:
                logger.warning(f"Failed to migrate secret '{config_key}': {e}")

        return migrated_config

    def _get_config_value(self, key: str) -> Any:
        """Get value from config using dot notation."""
        return self._get_nested_value(self.config, key)

    def _set_config_value(self, key: str, value: Any) -> None:
        """Set value in config using dot notation."""
        self._set_nested_value(self.config, key, value)

    def _has_config_value(self, key: str) -> bool:
        """Check if config key exists."""
        try:
            self._get_nested_value(self.config, key)
            return True
        except KeyError:
            return False

    def _remove_config_value(self, key: str) -> None:
        """Remove value from config using dot notation."""
        keys = key.split(".")
        config = self.config

        # Navigate to parent
        for k in keys[:-1]:
            if k not in config:
                return
            config = config[k]

        # Remove the key
        if keys[-1] in config:
            del config[keys[-1]]

    def _get_nested_value(self, data: Dict[str, Any], key: str) -> Any:
        """Get nested value using dot notation."""
        keys = key.split(".")
        value = data

        for k in keys:
            if not isinstance(value, dict) or k not in value:
                raise KeyError(f"Key '{key}' not found")
            value = value[k]

        return value

    def _set_nested_value(self, data: Dict[str, Any], key: str, value: Any) -> None:
        """Set nested value using dot notation."""
        keys = key.split(".")
        config = data

        # Navigate to parent, creating intermediate dicts as needed
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        # Set the value
        config[keys[-1]] = value
