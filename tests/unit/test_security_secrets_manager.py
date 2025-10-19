"""Tests for secrets management."""

import os
import tempfile
from unittest.mock import patch

import pytest
from pathlib import Path

from src.core.exceptions import ErrorSeverity, SecretsError
from src.security.secrets_manager import SecretsManager


class TestSecretsManager:
    """Test secrets manager functionality."""

    def test_initialization_creates_key_file(self):
        """Test that initialization creates encryption key file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            key_path = Path(temp_dir) / "test.key"
            secrets_manager = SecretsManager(key_path=key_path)

            assert key_path.exists()
            assert key_path.stat().st_mode & 0o777 == 0o600  # Check permissions

    def test_encrypt_decrypt_secret(self):
        """Test encrypting and decrypting secrets."""
        with tempfile.TemporaryDirectory() as temp_dir:
            key_path = Path(temp_dir) / "test.key"
            secrets_manager = SecretsManager(key_path=key_path)

            original_secret = "my_secret_password"
            encrypted = secrets_manager.encrypt_secret(original_secret)
            decrypted = secrets_manager.decrypt_secret(encrypted)

            assert encrypted != original_secret
            assert decrypted == original_secret

    def test_get_secret_from_environment(self):
        """Test getting secret from environment variable."""
        with tempfile.TemporaryDirectory() as temp_dir:
            key_path = Path(temp_dir) / "test.key"
            secrets_manager = SecretsManager(key_path=key_path)

            with patch.dict(os.environ, {"KINDLE_SYNC_SMTP_PASSWORD": "env_password"}):
                secret = secrets_manager.get_secret("smtp_password")
                assert secret == "env_password"

    def test_get_secret_from_config(self):
        """Test getting secret from encrypted config."""
        with tempfile.TemporaryDirectory() as temp_dir:
            key_path = Path(temp_dir) / "test.key"
            config = {"secrets": {"smtp_password": "encrypted_value"}}
            secrets_manager = SecretsManager(key_path=key_path, config=config)

            # Mock the decrypt method to return a known value
            with patch.object(
                secrets_manager, "decrypt_secret", return_value="decrypted_password"
            ):
                secret = secrets_manager.get_secret("smtp_password")
                assert secret == "decrypted_password"

    def test_get_secret_default_value(self):
        """Test getting default value when secret not found."""
        with tempfile.TemporaryDirectory() as temp_dir:
            key_path = Path(temp_dir) / "test.key"
            secrets_manager = SecretsManager(key_path=key_path)

            secret = secrets_manager.get_secret(
                "nonexistent_secret", default="default_value"
            )
            assert secret == "default_value"

    def test_set_secret(self):
        """Test setting a secret."""
        with tempfile.TemporaryDirectory() as temp_dir:
            key_path = Path(temp_dir) / "test.key"
            config = {}
            secrets_manager = SecretsManager(key_path=key_path, config=config)

            with patch.object(
                secrets_manager, "encrypt_secret", return_value="encrypted_value"
            ):
                secrets_manager.set_secret("test_secret", "test_value")

                # Check that the secret was stored in config
                assert "secrets" in config
                assert config["secrets"]["test_secret"] == "encrypted_value"

    def test_delete_secret(self):
        """Test deleting a secret."""
        with tempfile.TemporaryDirectory() as temp_dir:
            key_path = Path(temp_dir) / "test.key"
            config = {"secrets": {"test_secret": "encrypted_value"}}
            secrets_manager = SecretsManager(key_path=key_path, config=config)

            result = secrets_manager.delete_secret("test_secret")
            assert result is True
            assert "test_secret" not in config["secrets"]

    def test_delete_nonexistent_secret(self):
        """Test deleting a nonexistent secret."""
        with tempfile.TemporaryDirectory() as temp_dir:
            key_path = Path(temp_dir) / "test.key"
            config = {}
            secrets_manager = SecretsManager(key_path=key_path, config=config)

            result = secrets_manager.delete_secret("nonexistent_secret")
            assert result is False

    def test_list_secrets(self):
        """Test listing all secrets."""
        with tempfile.TemporaryDirectory() as temp_dir:
            key_path = Path(temp_dir) / "test.key"
            config = {
                "secrets": {
                    "secret1": "encrypted_value1",
                    "secret2": "encrypted_value2",
                }
            }
            secrets_manager = SecretsManager(key_path=key_path, config=config)

            secrets = secrets_manager.list_secrets()
            assert set(secrets) == {"secret1", "secret2"}

    def test_migrate_plaintext_secrets(self):
        """Test migrating plaintext secrets to encrypted storage."""
        with tempfile.TemporaryDirectory() as temp_dir:
            key_path = Path(temp_dir) / "test.key"
            secrets_manager = SecretsManager(key_path=key_path)

            plaintext_config = {"kindle": {"smtp_password": "plaintext_password"}}

            with patch.object(
                secrets_manager, "encrypt_secret", return_value="encrypted_password"
            ):
                migrated_config = secrets_manager.migrate_plaintext_secrets(
                    plaintext_config
                )

                assert (
                    migrated_config["kindle"]["smtp_password"]
                    == "encrypted:encrypted_password"
                )

    def test_encrypt_secret_error(self):
        """Test error handling in encrypt_secret."""
        with tempfile.TemporaryDirectory() as temp_dir:
            key_path = Path(temp_dir) / "test.key"
            secrets_manager = SecretsManager(key_path=key_path)

            # Mock cipher.encrypt to raise an exception
            with patch.object(
                secrets_manager.cipher,
                "encrypt",
                side_effect=Exception("Encryption failed"),
            ):
                with pytest.raises(SecretsError) as exc_info:
                    secrets_manager.encrypt_secret("test_secret")

                assert exc_info.value.severity == ErrorSeverity.HIGH
                assert "Failed to encrypt secret" in str(exc_info.value)

    def test_decrypt_secret_error(self):
        """Test error handling in decrypt_secret."""
        with tempfile.TemporaryDirectory() as temp_dir:
            key_path = Path(temp_dir) / "test.key"
            secrets_manager = SecretsManager(key_path=key_path)

            # Mock cipher.decrypt to raise an exception
            with patch.object(
                secrets_manager.cipher,
                "decrypt",
                side_effect=Exception("Decryption failed"),
            ):
                with pytest.raises(SecretsError) as exc_info:
                    secrets_manager.decrypt_secret("invalid_encrypted_secret")

                assert exc_info.value.severity == ErrorSeverity.HIGH
                assert "Failed to decrypt secret" in str(exc_info.value)

    def test_key_file_permissions(self):
        """Test that key file has correct permissions."""
        with tempfile.TemporaryDirectory() as temp_dir:
            key_path = Path(temp_dir) / "test.key"
            secrets_manager = SecretsManager(key_path=key_path)

            # Check that the key file has restrictive permissions
            stat = key_path.stat()
            permissions = stat.st_mode & 0o777
            assert permissions == 0o600  # Owner read/write only

    def test_nested_config_access(self):
        """Test accessing nested configuration values."""
        with tempfile.TemporaryDirectory() as temp_dir:
            key_path = Path(temp_dir) / "test.key"
            config = {"level1": {"level2": {"value": "test_value"}}}
            secrets_manager = SecretsManager(key_path=key_path, config=config)

            # Test _get_nested_value
            value = secrets_manager._get_nested_value(config, "level1.level2.value")
            assert value == "test_value"

            # Test _set_nested_value
            secrets_manager._set_nested_value(
                config, "level1.level2.new_value", "new_test_value"
            )
            assert config["level1"]["level2"]["new_value"] == "new_test_value"
