"""
Property-based tests for SettingsManager.

Feature: openai-cli-refactor
Tests settings persistence and round-trip consistency.
"""

import os
import tempfile
import shutil
import pytest
from pathlib import Path
from hypothesis import given, strategies as st, settings
from shello_cli.utils.settings_manager import SettingsManager, UserSettings, ProjectSettings


# Custom strategies for generating valid settings
@st.composite
def user_settings_strategy(draw):
    """Generate valid UserSettings instances with provider configs."""
    from shello_cli.utils.settings_manager import ProviderConfig
    
    # Generate OpenAI config
    api_key = draw(st.one_of(
        st.none(),
        st.text(min_size=10, max_size=100, alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd'),
            whitelist_characters='-_'
        ))
    ))
    
    base_url = draw(st.sampled_from([
        "https://api.openai.com/v1",
        "https://api.anthropic.com/v1",
        "http://localhost:8000/v1",
        "https://custom-api.example.com/v1"
    ]))
    
    default_model = draw(st.sampled_from([
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4-turbo",
        "gpt-4",
        "gpt-3.5-turbo"
    ]))
    
    models = draw(st.lists(
        st.sampled_from([
            "gpt-4o", "gpt-4o-mini", "gpt-4-turbo", 
            "gpt-4", "gpt-3.5-turbo"
        ]),
        min_size=1,
        max_size=10,
        unique=True
    ))
    
    openai_config = ProviderConfig(
        provider_type="openai",
        api_key=api_key,
        base_url=base_url,
        default_model=default_model,
        models=models
    )
    
    return UserSettings(
        provider="openai",
        openai_config=openai_config
    )


class TestSettingsManagerProperties:
    """Property-based tests for SettingsManager."""
    
    @given(user_settings=user_settings_strategy())
    @settings(max_examples=100, deadline=None)
    def test_property_4_settings_round_trip_consistency(self, user_settings):
        """
        Feature: openai-cli-refactor, Property 4: Settings Round-Trip Consistency
        
        For any valid UserSettings object, saving then loading the settings SHALL 
        produce an equivalent object (with defaults merged for any missing fields).
        
        Validates: Requirements 5.4, 5.5, 5.6
        """
        # Create a temporary directory for test settings
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a new SettingsManager instance with custom paths
            manager = SettingsManager()
            
            # Override the settings path to use temp directory
            original_user_path = manager._user_settings_path
            manager._user_settings_path = Path(temp_dir) / "user-settings.json"
            
            try:
                # Save the settings
                manager.save_user_settings(user_settings)
                
                # Clear cached settings to force reload
                manager._user_settings = None
                
                # Load the settings back
                loaded_settings = manager.load_user_settings()
                
                # Verify all fields match
                assert loaded_settings.provider == user_settings.provider, \
                    f"Provider mismatch: {loaded_settings.provider} != {user_settings.provider}"
                
                # Check openai_config if present
                if user_settings.openai_config:
                    assert loaded_settings.openai_config is not None
                    assert loaded_settings.openai_config.api_key == user_settings.openai_config.api_key
                    assert loaded_settings.openai_config.base_url == user_settings.openai_config.base_url
                    assert loaded_settings.openai_config.default_model == user_settings.openai_config.default_model
                    assert loaded_settings.openai_config.models == user_settings.openai_config.models
                
                # Verify file has secure permissions (user read/write only)
                file_stat = os.stat(manager._user_settings_path)
                file_mode = file_stat.st_mode & 0o777
                # On Windows, permission checks work differently, so we skip this check
                if os.name != 'nt':
                    assert file_mode == 0o600, \
                        f"File permissions should be 0o600, got {oct(file_mode)}"
            
            finally:
                # Restore original path
                manager._user_settings_path = original_user_path


class TestSettingsManagerUnitTests:
    """Unit tests for specific SettingsManager scenarios."""
    
    def test_load_nonexistent_user_settings_returns_defaults(self):
        """Test that loading nonexistent user settings returns defaults."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = SettingsManager()
            manager._user_settings_path = Path(temp_dir) / "nonexistent" / "user-settings.json"
            manager._user_settings = None
            
            settings = manager.load_user_settings()
            
            assert settings.provider == "openai"
            assert settings.openai_config is None
            assert settings.bedrock_config is None
    
    def test_load_nonexistent_project_settings_returns_defaults(self):
        """Test that loading nonexistent project settings returns defaults."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = SettingsManager()
            manager._project_settings_path = Path(temp_dir) / "nonexistent" / "settings.json"
            manager._project_settings = None
            
            settings = manager.load_project_settings()
            
            assert settings.model is None
    
    def test_save_and_load_user_settings(self):
        """Test saving and loading user settings."""
        from shello_cli.utils.settings_manager import ProviderConfig
        
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = SettingsManager()
            manager._user_settings_path = Path(temp_dir) / "user-settings.json"
            
            # Create test settings with openai_config
            openai_config = ProviderConfig(
                provider_type="openai",
                api_key="test-key-12345",
                base_url="https://test.example.com/v1",
                default_model="gpt-4",
                models=["gpt-4", "gpt-3.5-turbo"]
            )
            
            test_settings = UserSettings(
                provider="openai",
                openai_config=openai_config
            )
            
            # Save settings
            manager.save_user_settings(test_settings)
            
            # Clear cache and load
            manager._user_settings = None
            loaded = manager.load_user_settings()
            
            assert loaded.openai_config is not None
            assert loaded.openai_config.api_key == "test-key-12345"
            assert loaded.openai_config.base_url == "https://test.example.com/v1"
            assert loaded.openai_config.default_model == "gpt-4"
            assert loaded.openai_config.models == ["gpt-4", "gpt-3.5-turbo"]
    
    def test_save_and_load_project_settings(self):
        """Test saving and loading project settings."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = SettingsManager()
            manager._project_settings_path = Path(temp_dir) / "settings.json"
            
            # Create test settings
            test_settings = ProjectSettings(model="gpt-4o-mini")
            
            # Save settings
            manager.save_project_settings(test_settings)
            
            # Clear cache and load
            manager._project_settings = None
            loaded = manager.load_project_settings()
            
            assert loaded.model == "gpt-4o-mini"
    
    def test_get_api_key_from_environment(self):
        """Test that get_api_key prioritizes environment variable."""
        from shello_cli.utils.settings_manager import ProviderConfig
        
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = SettingsManager()
            manager._user_settings_path = Path(temp_dir) / "user-settings.json"
            
            # Save settings with API key in openai_config
            openai_config = ProviderConfig(
                provider_type="openai",
                api_key="settings-key"
            )
            test_settings = UserSettings(
                provider="openai",
                openai_config=openai_config
            )
            manager.save_user_settings(test_settings)
            
            # Set environment variable
            os.environ['OPENAI_API_KEY'] = "env-key"
            
            try:
                # Clear cache
                manager._user_settings = None
                
                # Should return environment variable
                api_key = manager.get_api_key()
                assert api_key == "env-key"
            finally:
                # Clean up environment
                del os.environ['OPENAI_API_KEY']
    
    def test_get_api_key_from_settings(self):
        """Test that get_api_key falls back to settings."""
        from shello_cli.utils.settings_manager import ProviderConfig
        
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = SettingsManager()
            manager._user_settings_path = Path(temp_dir) / "user-settings.json"
            
            # Ensure no environment variable
            if 'OPENAI_API_KEY' in os.environ:
                del os.environ['OPENAI_API_KEY']
            
            # Save settings with API key in openai_config
            openai_config = ProviderConfig(
                provider_type="openai",
                api_key="settings-key"
            )
            test_settings = UserSettings(
                provider="openai",
                openai_config=openai_config
            )
            manager.save_user_settings(test_settings)
            
            # Clear cache
            manager._user_settings = None
            
            # Should return settings key
            api_key = manager.get_api_key()
            assert api_key == "settings-key"
    
    def test_get_current_model_priority(self):
        """Test that get_current_model follows priority: project > user > default."""
        from shello_cli.utils.settings_manager import ProviderConfig
        
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = SettingsManager()
            manager._user_settings_path = Path(temp_dir) / "user-settings.json"
            manager._project_settings_path = Path(temp_dir) / "settings.json"
            
            # Test 1: No settings, should return default
            manager._user_settings = None
            manager._project_settings = None
            model = manager.get_current_model()
            assert model == "gpt-4o"
            
            # Test 2: User settings only
            openai_config = ProviderConfig(
                provider_type="openai",
                default_model="gpt-4-turbo"
            )
            user_settings = UserSettings(
                provider="openai",
                openai_config=openai_config
            )
            manager.save_user_settings(user_settings)
            manager._user_settings = None
            manager._project_settings = None
            model = manager.get_current_model()
            assert model == "gpt-4-turbo"
            
            # Test 3: Project settings override user settings
            project_settings = ProjectSettings(model="gpt-3.5-turbo")
            manager.save_project_settings(project_settings)
            manager._user_settings = None
            manager._project_settings = None
            model = manager.get_current_model()
            assert model == "gpt-3.5-turbo"
    
    def test_get_base_url(self):
        """Test that get_base_url returns configured URL."""
        from shello_cli.utils.settings_manager import ProviderConfig
        
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = SettingsManager()
            manager._user_settings_path = Path(temp_dir) / "user-settings.json"
            
            # Save settings with custom base URL in openai_config
            openai_config = ProviderConfig(
                provider_type="openai",
                base_url="https://custom.example.com/v1"
            )
            test_settings = UserSettings(
                provider="openai",
                openai_config=openai_config
            )
            manager.save_user_settings(test_settings)
            
            # Clear cache
            manager._user_settings = None
            
            # Should return custom URL
            base_url = manager.get_base_url()
            assert base_url == "https://custom.example.com/v1"
    
    def test_singleton_pattern(self):
        """Test that SettingsManager follows singleton pattern."""
        instance1 = SettingsManager.get_instance()
        instance2 = SettingsManager.get_instance()
        
        assert instance1 is instance2
    
    def test_corrupted_settings_file_returns_defaults(self):
        """Test that corrupted settings file returns defaults."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = SettingsManager()
            manager._user_settings_path = Path(temp_dir) / "user-settings.json"
            
            # Write corrupted JSON
            manager._user_settings_path.parent.mkdir(parents=True, exist_ok=True)
            with open(manager._user_settings_path, 'w') as f:
                f.write("{ invalid json }")
            
            # Clear cache
            manager._user_settings = None
            
            # Should return defaults without crashing
            settings = manager.load_user_settings()
            assert settings.provider == "openai"
            assert settings.openai_config is None


class TestCommandTrustConfigLoading:
    """Unit tests for command_trust configuration loading."""
    
    def test_load_with_command_trust_present(self):
        """Test loading settings with command_trust configuration present."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = SettingsManager()
            manager._user_settings_path = Path(temp_dir) / "user-settings.json"
            
            # Create settings file with command_trust
            manager._user_settings_path.parent.mkdir(parents=True, exist_ok=True)
            import json
            with open(manager._user_settings_path, 'w') as f:
                json.dump({
                    "api_key": "test-key",
                    "command_trust": {
                        "enabled": True,
                        "yolo_mode": False,
                        "approval_mode": "ai_driven",
                        "allowlist": ["ls", "pwd", "git status"],
                        "denylist": ["rm -rf *"]
                    }
                }, f)
            
            # Clear cache and load
            manager._user_settings = None
            settings = manager.load_user_settings()
            
            assert settings.command_trust is not None
            assert settings.command_trust.enabled is True
            assert settings.command_trust.yolo_mode is False
            assert settings.command_trust.approval_mode == "ai_driven"
            assert settings.command_trust.allowlist == ["ls", "pwd", "git status"]
            # Denylist should include defaults + user patterns
            assert "rm -rf *" in settings.command_trust.denylist
            assert "rm -rf /" in settings.command_trust.denylist  # Default pattern
    
    def test_load_without_command_trust_returns_none(self):
        """Test loading settings without command_trust returns None for command_trust."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = SettingsManager()
            manager._user_settings_path = Path(temp_dir) / "user-settings.json"
            
            # Create settings file without command_trust
            manager._user_settings_path.parent.mkdir(parents=True, exist_ok=True)
            import json
            with open(manager._user_settings_path, 'w') as f:
                json.dump({
                    "api_key": "test-key",
                    "base_url": "https://api.openai.com/v1"
                }, f)
            
            # Clear cache and load
            manager._user_settings = None
            settings = manager.load_user_settings()
            
            assert settings.command_trust is None
    
    def test_denylist_additive_merging(self):
        """Test that user denylist patterns are added to defaults (additive merging)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = SettingsManager()
            manager._user_settings_path = Path(temp_dir) / "user-settings.json"
            
            # Create settings with custom denylist
            manager._user_settings_path.parent.mkdir(parents=True, exist_ok=True)
            import json
            with open(manager._user_settings_path, 'w') as f:
                json.dump({
                    "command_trust": {
                        "denylist": ["sudo rm -rf *", "git push --force"]
                    }
                }, f)
            
            # Clear cache and load
            manager._user_settings = None
            settings = manager.load_user_settings()
            
            # Should have both default and user patterns
            assert "sudo rm -rf *" in settings.command_trust.denylist
            assert "git push --force" in settings.command_trust.denylist
            assert "rm -rf /" in settings.command_trust.denylist  # Default
            assert "dd if=/dev/zero*" in settings.command_trust.denylist  # Default
    
    def test_allowlist_override(self):
        """Test that user allowlist completely replaces defaults."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = SettingsManager()
            manager._user_settings_path = Path(temp_dir) / "user-settings.json"
            
            # Create settings with custom allowlist
            manager._user_settings_path.parent.mkdir(parents=True, exist_ok=True)
            import json
            with open(manager._user_settings_path, 'w') as f:
                json.dump({
                    "command_trust": {
                        "allowlist": ["custom command", "another command"]
                    }
                }, f)
            
            # Clear cache and load
            manager._user_settings = None
            settings = manager.load_user_settings()
            
            # Should only have user patterns, not defaults
            assert settings.command_trust.allowlist == ["custom command", "another command"]
            assert "ls" not in settings.command_trust.allowlist  # Default should not be present
    
    def test_get_command_trust_config_with_config(self):
        """Test get_command_trust_config returns configured values."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = SettingsManager()
            manager._user_settings_path = Path(temp_dir) / "user-settings.json"
            
            # Create settings with command_trust
            manager._user_settings_path.parent.mkdir(parents=True, exist_ok=True)
            import json
            with open(manager._user_settings_path, 'w') as f:
                json.dump({
                    "command_trust": {
                        "enabled": False,
                        "yolo_mode": True,
                        "approval_mode": "user_driven"
                    }
                }, f)
            
            # Clear cache
            manager._user_settings = None
            
            # Get config
            config = manager.get_command_trust_config()
            
            assert config.enabled is False
            assert config.yolo_mode is True
            assert config.approval_mode == "user_driven"
    
    def test_get_command_trust_config_without_config_returns_defaults(self):
        """Test get_command_trust_config returns defaults when not configured."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = SettingsManager()
            manager._user_settings_path = Path(temp_dir) / "user-settings.json"
            
            # Create settings without command_trust
            manager._user_settings_path.parent.mkdir(parents=True, exist_ok=True)
            import json
            with open(manager._user_settings_path, 'w') as f:
                json.dump({"api_key": "test-key"}, f)
            
            # Clear cache
            manager._user_settings = None
            
            # Get config
            config = manager.get_command_trust_config()
            
            # Should return defaults
            assert config.enabled is True
            assert config.yolo_mode is False
            assert config.approval_mode == "user_driven"
            assert "ls" in config.allowlist
            assert "rm -rf /" in config.denylist
    
    def test_save_user_settings_with_command_trust(self):
        """Test saving user settings with command_trust configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = SettingsManager()
            manager._user_settings_path = Path(temp_dir) / "user-settings.json"
            
            from shello_cli.utils.settings_manager import UserSettings, CommandTrustConfig, ProviderConfig
            
            # Create settings with command_trust
            command_trust = CommandTrustConfig(
                enabled=True,
                yolo_mode=False,
                approval_mode="ai_driven",
                allowlist=["ls", "pwd"],
                denylist=["rm -rf /", "custom dangerous"]
            )
            
            openai_config = ProviderConfig(
                provider_type="openai",
                api_key="test-key"
            )
            
            test_settings = UserSettings(
                provider="openai",
                openai_config=openai_config,
                command_trust=command_trust
            )
            
            # Save settings
            manager.save_user_settings(test_settings)
            
            # Load and verify
            manager._user_settings = None
            loaded = manager.load_user_settings()
            
            assert loaded.command_trust is not None
            assert loaded.command_trust.enabled is True
            assert loaded.command_trust.yolo_mode is False
            assert loaded.command_trust.approval_mode == "ai_driven"
            assert loaded.command_trust.allowlist == ["ls", "pwd"]
            assert "custom dangerous" in loaded.command_trust.denylist
    
    def test_denylist_no_duplicates(self):
        """Test that duplicate patterns in user denylist are not added twice."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = SettingsManager()
            manager._user_settings_path = Path(temp_dir) / "user-settings.json"
            
            # Create settings with denylist that includes a default pattern
            manager._user_settings_path.parent.mkdir(parents=True, exist_ok=True)
            import json
            with open(manager._user_settings_path, 'w') as f:
                json.dump({
                    "command_trust": {
                        "denylist": ["rm -rf /", "custom pattern"]  # "rm -rf /" is a default
                    }
                }, f)
            
            # Clear cache and load
            manager._user_settings = None
            settings = manager.load_user_settings()
            
            # Count occurrences of "rm -rf /"
            count = settings.command_trust.denylist.count("rm -rf /")
            assert count == 1, f"Expected 1 occurrence of 'rm -rf /', got {count}"
            assert "custom pattern" in settings.command_trust.denylist

    def test_enable_yolo_mode_for_session(self):
        """Test enabling YOLO mode for the current session without persisting."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = SettingsManager()
            manager._user_settings_path = Path(temp_dir) / "user-settings.json"
            
            # Create settings without YOLO mode
            manager._user_settings_path.parent.mkdir(parents=True, exist_ok=True)
            import json
            with open(manager._user_settings_path, 'w') as f:
                json.dump({
                    "api_key": "test-key",
                    "command_trust": {
                        "yolo_mode": False
                    }
                }, f)
            
            # Clear cache and load
            manager._user_settings = None
            settings = manager.load_user_settings()
            assert settings.command_trust.yolo_mode is False
            
            # Enable YOLO mode for session
            manager.enable_yolo_mode_for_session()
            
            # Verify YOLO mode is enabled in memory
            config = manager.get_command_trust_config()
            assert config.yolo_mode is True
            
            # Verify it's NOT persisted to file
            manager._user_settings = None
            reloaded = manager.load_user_settings()
            assert reloaded.command_trust.yolo_mode is False
    
    def test_enable_yolo_mode_for_session_without_command_trust(self):
        """Test enabling YOLO mode when command_trust is not configured."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = SettingsManager()
            manager._user_settings_path = Path(temp_dir) / "user-settings.json"
            
            # Create settings without command_trust
            manager._user_settings_path.parent.mkdir(parents=True, exist_ok=True)
            import json
            with open(manager._user_settings_path, 'w') as f:
                json.dump({
                    "api_key": "test-key"
                }, f)
            
            # Clear cache and load
            manager._user_settings = None
            settings = manager.load_user_settings()
            assert settings.command_trust is None
            
            # Enable YOLO mode for session
            manager.enable_yolo_mode_for_session()
            
            # Verify YOLO mode is enabled in memory with defaults
            config = manager.get_command_trust_config()
            assert config.yolo_mode is True
            assert config.enabled is True
            assert config.approval_mode == "user_driven"
