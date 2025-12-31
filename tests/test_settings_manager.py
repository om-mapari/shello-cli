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
    """Generate valid UserSettings instances."""
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
        "gpt-3.5-turbo",
        "claude-3-opus"
    ]))
    
    models = draw(st.lists(
        st.sampled_from([
            "gpt-4o", "gpt-4o-mini", "gpt-4-turbo", 
            "gpt-4", "gpt-3.5-turbo", "claude-3-opus"
        ]),
        min_size=1,
        max_size=10,
        unique=True
    ))
    
    return UserSettings(
        api_key=api_key,
        base_url=base_url,
        default_model=default_model,
        models=models
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
                assert loaded_settings.api_key == user_settings.api_key, \
                    f"API key mismatch: {loaded_settings.api_key} != {user_settings.api_key}"
                
                assert loaded_settings.base_url == user_settings.base_url, \
                    f"Base URL mismatch: {loaded_settings.base_url} != {user_settings.base_url}"
                
                assert loaded_settings.default_model == user_settings.default_model, \
                    f"Default model mismatch: {loaded_settings.default_model} != {user_settings.default_model}"
                
                assert loaded_settings.models == user_settings.models, \
                    f"Models list mismatch: {loaded_settings.models} != {user_settings.models}"
                
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
            
            assert settings.api_key is None
            assert settings.base_url == "https://api.openai.com/v1"
            assert settings.default_model == "gpt-4o"
            assert "gpt-4o" in settings.models
    
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
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = SettingsManager()
            manager._user_settings_path = Path(temp_dir) / "user-settings.json"
            
            # Create test settings
            test_settings = UserSettings(
                api_key="test-key-12345",
                base_url="https://test.example.com/v1",
                default_model="gpt-4",
                models=["gpt-4", "gpt-3.5-turbo"]
            )
            
            # Save settings
            manager.save_user_settings(test_settings)
            
            # Clear cache and load
            manager._user_settings = None
            loaded = manager.load_user_settings()
            
            assert loaded.api_key == "test-key-12345"
            assert loaded.base_url == "https://test.example.com/v1"
            assert loaded.default_model == "gpt-4"
            assert loaded.models == ["gpt-4", "gpt-3.5-turbo"]
    
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
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = SettingsManager()
            manager._user_settings_path = Path(temp_dir) / "user-settings.json"
            
            # Save settings with API key
            test_settings = UserSettings(api_key="settings-key")
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
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = SettingsManager()
            manager._user_settings_path = Path(temp_dir) / "user-settings.json"
            
            # Ensure no environment variable
            if 'OPENAI_API_KEY' in os.environ:
                del os.environ['OPENAI_API_KEY']
            
            # Save settings with API key
            test_settings = UserSettings(api_key="settings-key")
            manager.save_user_settings(test_settings)
            
            # Clear cache
            manager._user_settings = None
            
            # Should return settings key
            api_key = manager.get_api_key()
            assert api_key == "settings-key"
    
    def test_get_current_model_priority(self):
        """Test that get_current_model follows priority: project > user > default."""
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
            user_settings = UserSettings(default_model="gpt-4-turbo")
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
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = SettingsManager()
            manager._user_settings_path = Path(temp_dir) / "user-settings.json"
            
            # Save settings with custom base URL
            test_settings = UserSettings(base_url="https://custom.example.com/v1")
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
            assert settings.api_key is None
            assert settings.base_url == "https://api.openai.com/v1"
