"""Integration tests for configuration system."""

import pytest
import yaml
from pathlib import Path
from unittest.mock import patch

from src.config import Config


class TestConfigIntegration:
    """Integration tests for Config class with real file operations."""

    def test_config_with_real_file_operations(self, temp_dir):
        """Test Config with real file operations."""
        # Create a real config file
        config_data = {
            "obsidian": {
                "vault_path": str(temp_dir / "obsidian_vault"),
                "sync_folder": "Kindle Sync",
                "templates_folder": "Templates"
            },
            "kindle": {
                "email": "test@kindle.com",
                "approved_senders": ["test@example.com"],
                "smtp_server": "smtp.gmail.com",
                "smtp_port": 587,
                "smtp_username": "test@gmail.com",
                "smtp_password": "test_password"
            },
            "processing": {
                "ocr": {"language": "eng"},
                "pdf": {"page_size": "A4"},
                "markdown": {"extensions": ["tables"]}
            },
            "sync": {"auto_convert_on_save": True},
            "patterns": {"markdown_files": "*.md"},
            "logging": {"level": "INFO"},
            "advanced": {"debounce_time": 1.0}
        }
        
        config_file = temp_dir / "config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)
        
        # Create the vault directory
        vault_path = temp_dir / "obsidian_vault"
        vault_path.mkdir()
        
        # Test Config initialization
        config = Config(str(config_file))
        
        # Test path expansion
        assert config.get_obsidian_vault_path() == vault_path.resolve()
        
        # Test folder path generation
        sync_path = config.get_sync_folder_path()
        assert sync_path == vault_path / "Kindle Sync"
        
        templates_path = config.get_templates_folder_path()
        assert templates_path == vault_path / "Templates"
        
        # Test validation
        assert config.validate() is True

    def test_config_with_missing_vault_path(self, temp_dir):
        """Test Config validation with missing vault path."""
        config_data = {
            "obsidian": {
                "vault_path": "/non/existent/path",
                "sync_folder": "Kindle Sync"
            },
            "kindle": {
                "email": "test@kindle.com",
                "smtp_server": "smtp.gmail.com",
                "smtp_username": "test@gmail.com",
                "smtp_password": "test_password"
            }
        }
        
        config_file = temp_dir / "config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)
        
        config = Config(str(config_file))
        
        # Validation should fail
        assert config.validate() is False

    def test_config_with_invalid_email(self, temp_dir):
        """Test Config validation with invalid email."""
        # Create vault directory
        vault_path = temp_dir / "obsidian_vault"
        vault_path.mkdir()
        
        config_data = {
            "obsidian": {
                "vault_path": str(vault_path),
                "sync_folder": "Kindle Sync"
            },
            "kindle": {
                "email": "invalid-email",  # Invalid email
                "smtp_server": "smtp.gmail.com",
                "smtp_username": "test@gmail.com",
                "smtp_password": "test_password"
            }
        }
        
        config_file = temp_dir / "config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)
        
        config = Config(str(config_file))
        
        # Validation should fail
        assert config.validate() is False

    def test_config_with_missing_smtp_config(self, temp_dir):
        """Test Config validation with missing SMTP configuration."""
        # Create vault directory
        vault_path = temp_dir / "obsidian_vault"
        vault_path.mkdir()
        
        config_data = {
            "obsidian": {
                "vault_path": str(vault_path),
                "sync_folder": "Kindle Sync"
            },
            "kindle": {
                "email": "test@kindle.com",
                "smtp_server": "",  # Missing SMTP server
                "smtp_username": "",
                "smtp_password": ""
            }
        }
        
        config_file = temp_dir / "config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)
        
        config = Config(str(config_file))
        
        # Validation should fail
        assert config.validate() is False

    def test_config_path_expansion_with_tilde(self, temp_dir):
        """Test path expansion with tilde notation."""
        config_data = {
            "obsidian": {
                "vault_path": "~/test_vault"
            },
            "sync": {
                "backup_folder": "~/backups"
            }
        }
        
        config_file = temp_dir / "config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)
        
        # Mock home directory
        with patch('pathlib.Path.expanduser') as mock_expand:
            mock_expand.return_value = temp_dir / "home" / "user" / "test_vault"
            
            config = Config(str(config_file))
            
            # Verify expanduser was called
            mock_expand.assert_called()

    def test_config_nested_key_access(self, temp_dir):
        """Test accessing deeply nested configuration keys."""
        config_data = {
            "level1": {
                "level2": {
                    "level3": {
                        "value": "deep_value"
                    }
                }
            }
        }
        
        config_file = temp_dir / "config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)
        
        config = Config(str(config_file))
        
        # Test nested key access
        assert config.get('level1.level2.level3.value') == 'deep_value'
        assert config.get('level1.level2.level3') == {'value': 'deep_value'}
        assert config.get('level1.level2') == {'level3': {'value': 'deep_value'}}
        assert config.get('level1') == {'level2': {'level3': {'value': 'deep_value'}}}
        
        # Test non-existent nested key
        assert config.get('level1.level2.non_existent') is None
        assert config.get('level1.non_existent.level3') is None
        assert config.get('non_existent.level2.level3') is None

    def test_config_with_complex_data_types(self, temp_dir):
        """Test Config with complex data types."""
        config_data = {
            "lists": [1, 2, 3, "string", True],
            "nested_lists": [[1, 2], [3, 4], ["a", "b"]],
            "mixed_dict": {
                "string": "value",
                "number": 42,
                "boolean": True,
                "list": [1, 2, 3],
                "nested": {
                    "key": "value"
                }
            },
            "special_values": {
                "null_value": None,
                "empty_string": "",
                "zero": 0,
                "false": False
            }
        }
        
        config_file = temp_dir / "config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)
        
        config = Config(str(config_file))
        
        # Test list access
        assert config.get('lists') == [1, 2, 3, "string", True]
        assert config.get('nested_lists') == [[1, 2], [3, 4], ["a", "b"]] 
        
        # Test mixed dict access
        assert config.get('mixed_dict.string') == "value"
        assert config.get('mixed_dict.number') == 42
        assert config.get('mixed_dict.boolean') is True
        assert config.get('mixed_dict.list') == [1, 2, 3]
        assert config.get('mixed_dict.nested.key') == "value"
        
        # Test special values
        assert config.get('special_values.null_value') is None
        assert config.get('special_values.empty_string') == ""
        assert config.get('special_values.zero') == 0
        assert config.get('special_values.false') is False

    def test_config_file_permissions(self, temp_dir):
        """Test Config with different file permissions."""
        config_data = {"test": "value"}
        config_file = temp_dir / "config.yaml"
        
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)
        
        # Test with readable file
        config = Config(str(config_file))
        assert config.get('test') == "value"
        
        # Test with non-readable file (simulate permission error)
        import os
        os.chmod(config_file, 0o000)  # Remove all permissions
        
        try:
            with pytest.raises(PermissionError):
                Config(str(config_file))
        finally:
            # Restore permissions for cleanup
            os.chmod(config_file, 0o644)

    def test_config_large_file(self, temp_dir):
        """Test Config with a large configuration file."""
        # Create a large config with many nested sections
        config_data = {}
        
        for i in range(100):
            config_data[f"section_{i}"] = {
                f"key_{j}": f"value_{i}_{j}"
                for j in range(10)
            }
        
        config_file = temp_dir / "large_config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)
        
        # Test loading large config
        config = Config(str(config_file))
        
        # Test accessing various keys
        assert config.get('section_0.key_0') == "value_0_0"
        assert config.get('section_50.key_5') == "value_50_5"
        assert config.get('section_99.key_9') == "value_99_9"
        
        # Test accessing entire sections
        section_0 = config.get('section_0')
        assert len(section_0) == 10
        assert section_0['key_0'] == "value_0_0"

    def test_config_unicode_content(self, temp_dir):
        """Test Config with Unicode content."""
        config_data = {
            "unicode_strings": {
                "english": "Hello, World!",
                "chinese": "你好，世界！",
                "japanese": "こんにちは、世界！",
                "arabic": "مرحبا بالعالم!",
                "emoji": "🚀📚💻",
                "special_chars": "Café naïve résumé"
            },
            "unicode_keys": {
                "ключ": "значение",
                "clé": "valeur"
            }
        }
        
        config_file = temp_dir / "unicode_config.yaml"
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump(config_data, f, allow_unicode=True)
        
        # Test loading Unicode config
        config = Config(str(config_file))
        
        # Test Unicode string access
        assert config.get('unicode_strings.english') == "Hello, World!"
        assert config.get('unicode_strings.chinese') == "你好，世界！"
        assert config.get('unicode_strings.japanese') == "こんにちは、世界！"
        assert config.get('unicode_strings.arabic') == "مرحبا بالعالم!"
        assert config.get('unicode_strings.emoji') == "🚀📚💻"
        assert config.get('unicode_strings.special_chars') == "Café naïve résumé"
        
        # Test Unicode key access
        assert config.get('unicode_keys.ключ') == "значение"
        assert config.get('unicode_keys.clé') == "valeur"
