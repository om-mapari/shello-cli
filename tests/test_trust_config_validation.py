"""Unit tests for trust configuration validation."""

import pytest
from shello_cli.trust.trust_manager import TrustConfig, TrustConfigError, validate_config
from shello_cli.defaults import DEFAULT_ALLOWLIST, DEFAULT_DENYLIST


class TestTrustConfigValidation:
    """Test validate_config function."""
    
    def test_valid_config_ai_driven(self):
        """Test that valid ai_driven config passes validation."""
        config = TrustConfig(approval_mode="ai_driven")
        # Should not raise
        validate_config(config)
    
    def test_valid_config_user_driven(self):
        """Test that valid user_driven config passes validation."""
        config = TrustConfig(approval_mode="user_driven")
        # Should not raise
        validate_config(config)
    
    def test_invalid_approval_mode(self):
        """Test that invalid approval_mode raises TrustConfigError."""
        config = TrustConfig(approval_mode="invalid_mode")
        
        with pytest.raises(TrustConfigError) as exc_info:
            validate_config(config)
        
        assert "Invalid approval_mode" in str(exc_info.value)
        assert "invalid_mode" in str(exc_info.value)
        assert "ai_driven" in str(exc_info.value)
        assert "user_driven" in str(exc_info.value)
    
    def test_invalid_regex_in_allowlist(self):
        """Test that invalid regex pattern in allowlist raises TrustConfigError."""
        config = TrustConfig(allowlist=["^[invalid"])
        
        with pytest.raises(TrustConfigError) as exc_info:
            validate_config(config)
        
        assert "Invalid regex pattern in allowlist" in str(exc_info.value)
        assert "^[invalid" in str(exc_info.value)
    
    def test_invalid_regex_in_denylist(self):
        """Test that invalid regex pattern in denylist raises TrustConfigError."""
        config = TrustConfig(denylist=["^(unclosed"])
        
        with pytest.raises(TrustConfigError) as exc_info:
            validate_config(config)
        
        assert "Invalid regex pattern in denylist" in str(exc_info.value)
        assert "^(unclosed" in str(exc_info.value)
    
    def test_valid_regex_patterns(self):
        """Test that valid regex patterns pass validation."""
        config = TrustConfig(
            allowlist=["^git (status|log)$", "ls *", "pwd"],
            denylist=["^rm -rf /$", "^dd if=.*"]
        )
        # Should not raise
        validate_config(config)
    
    def test_non_regex_patterns_pass(self):
        """Test that non-regex patterns (exact and wildcard) pass validation."""
        config = TrustConfig(
            allowlist=["ls", "ls *", "git status"],
            denylist=["rm -rf /", "dd if=/dev/zero*"]
        )
        # Should not raise
        validate_config(config)
    
    def test_empty_lists_pass(self):
        """Test that empty allowlist and denylist pass validation."""
        config = TrustConfig(allowlist=[], denylist=[])
        # Should not raise
        validate_config(config)
    
    def test_default_config_passes(self):
        """Test that default TrustConfig passes validation."""
        config = TrustConfig()
        # Should not raise
        validate_config(config)


@pytest.mark.no_mock_settings
class TestSettingsManagerValidation:
    """Test that SettingsManager validates command_trust configuration."""
    
    def test_invalid_approval_mode_falls_back_to_defaults(self, tmp_path, capsys):
        """Test that invalid approval_mode falls back to defaults with warning."""
        from shello_cli.settings import SettingsManager
        
        # Create a settings file with invalid approval_mode
        settings_file = tmp_path / "user-settings.json"
        settings_file.write_text('''{
            "command_trust": {
                "approval_mode": "invalid_mode"
            }
        }''')
        
        # Create settings manager with custom path
        manager = SettingsManager()
        manager._user_settings_path = settings_file
        manager._user_settings = None  # Clear cache
        
        # Load settings
        user_settings = manager.load_user_settings()
        
        # Should fall back to defaults
        assert user_settings.command_trust is not None
        assert user_settings.command_trust.approval_mode == "user_driven"
        assert user_settings.command_trust.allowlist == DEFAULT_ALLOWLIST
        assert user_settings.command_trust.denylist == DEFAULT_DENYLIST
        
        # Should display warning
        captured = capsys.readouterr()
        assert "Warning: Invalid approval_mode" in captured.out
        assert "Using default 'user_driven'" in captured.out
    
    def test_invalid_regex_falls_back_to_defaults(self, tmp_path, capsys):
        """Test that invalid regex pattern is accepted (validation happens at use time)."""
        from shello_cli.settings import SettingsManager
        
        # Create a settings file with invalid regex
        settings_file = tmp_path / "user-settings.json"
        settings_file.write_text('''{
            "command_trust": {
                "allowlist": ["^[invalid"]
            }
        }''')
        
        # Create settings manager with custom path
        manager = SettingsManager()
        manager._user_settings_path = settings_file
        manager._user_settings = None  # Clear cache
        
        # Load settings
        user_settings = manager.load_user_settings()
        
        # Invalid regex is accepted (will fail at use time in PatternMatcher)
        assert user_settings.command_trust is not None
        assert user_settings.command_trust.approval_mode == "user_driven"
        assert user_settings.command_trust.allowlist == ["^[invalid"]  # Accepted as-is
        assert user_settings.command_trust.denylist == DEFAULT_DENYLIST  # Defaults used
    
    def test_valid_config_loads_successfully(self, tmp_path):
        """Test that valid command_trust config loads without warnings."""
        from shello_cli.settings import SettingsManager
        
        # Create a settings file with valid config
        settings_file = tmp_path / "user-settings.json"
        settings_file.write_text('''{
            "command_trust": {
                "approval_mode": "ai_driven",
                "allowlist": ["ls", "pwd", "^git (status|log)$"],
                "denylist": ["rm -rf /"]
            }
        }''')
        
        # Create settings manager with custom path
        manager = SettingsManager()
        manager._user_settings_path = settings_file
        manager._user_settings = None  # Clear cache
        
        # Load settings
        user_settings = manager.load_user_settings()
        
        # Should load successfully
        assert user_settings.command_trust is not None
        assert user_settings.command_trust.approval_mode == "ai_driven"
        assert "ls" in user_settings.command_trust.allowlist
        assert "pwd" in user_settings.command_trust.allowlist
        assert "^git (status|log)$" in user_settings.command_trust.allowlist
        # Denylist should include both defaults and user patterns
        assert "rm -rf /" in user_settings.command_trust.denylist
        assert "rm -rf /*" in user_settings.command_trust.denylist  # From defaults
    
    def test_missing_command_trust_uses_defaults(self, tmp_path):
        """Test that missing command_trust section uses defaults."""
        from shello_cli.settings import SettingsManager
        
        # Create a settings file without command_trust
        settings_file = tmp_path / "user-settings.json"
        settings_file.write_text('''{
            "default_model": "gpt-4o"
        }''')
        
        # Create settings manager with custom path
        manager = SettingsManager()
        manager._user_settings_path = settings_file
        manager._user_settings = None  # Clear cache
        
        # Load settings
        user_settings = manager.load_user_settings()
        
        # command_trust should be None (will use defaults via get_command_trust_config)
        assert user_settings.command_trust is None
        
        # get_command_trust_config should return defaults
        config = manager.get_command_trust_config()
        assert config.approval_mode == "user_driven"
        assert config.allowlist == DEFAULT_ALLOWLIST
        assert config.denylist == DEFAULT_DENYLIST
