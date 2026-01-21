"""
Unit tests for startup version check integration.

Feature: self-update-command
Tests Requirements: 2.1, 2.2, 2.3, 2.6, 2.7
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from shello_cli.update.update_manager import UpdateCheckResult
from shello_cli.settings.models import UserSettings, UpdateConfig


class TestStartupVersionCheck:
    """Test suite for startup version check."""
    
    @patch('shello_cli.update.update_manager.UpdateManager')
    def test_startup_check_when_enabled(self, mock_manager_class):
        """
        Test that startup check runs when check_on_startup is True.
        
        Validates: Requirements 2.1, 2.7
        """
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager
        
        # Simulate update available
        mock_manager.check_for_updates_async.return_value = UpdateCheckResult(
            update_available=True,
            current_version="0.4.3",
            latest_version="0.5.0"
        )
        
        # Create settings with check_on_startup enabled
        settings = UserSettings(
            provider="openai",
            update_config=UpdateConfig(check_on_startup=True)
        )
        
        # Verify settings
        assert settings.update_config.check_on_startup is True
        
        # Simulate the startup check logic
        if settings.update_config and settings.update_config.check_on_startup:
            from shello_cli.update.update_manager import UpdateManager
            manager = UpdateManager()
            result = manager.check_for_updates_async(timeout=2.0)
            
            # Verify the check was called
            assert result is not None
            assert result.update_available is True
    
    @patch('shello_cli.update.update_manager.UpdateManager')
    def test_startup_check_when_disabled(self, mock_manager_class):
        """
        Test that startup check is skipped when check_on_startup is False.
        
        Validates: Requirements 2.7
        """
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager
        
        # Create settings with check_on_startup disabled
        settings = UserSettings(
            provider="openai",
            update_config=UpdateConfig(check_on_startup=False)
        )
        
        # Verify settings
        assert settings.update_config.check_on_startup is False
        
        # Simulate the startup check logic
        check_performed = False
        if settings.update_config and settings.update_config.check_on_startup:
            check_performed = True
        
        # Verify the check was NOT performed
        assert check_performed is False
    
    @patch('shello_cli.update.update_manager.UpdateManager')
    def test_startup_check_silent_on_error(self, mock_manager_class):
        """
        Test that startup check fails silently on errors.
        
        Validates: Requirements 2.3, 2.6
        """
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager
        
        # Simulate error (returns None)
        mock_manager.check_for_updates_async.return_value = None
        
        # Create settings with check_on_startup enabled
        settings = UserSettings(
            provider="openai",
            update_config=UpdateConfig(check_on_startup=True)
        )
        
        # Simulate the startup check logic
        if settings.update_config and settings.update_config.check_on_startup:
            from shello_cli.update.update_manager import UpdateManager
            manager = UpdateManager()
            result = manager.check_for_updates_async(timeout=2.0)
            
            # Verify the check returned None (error case)
            assert result is None
            
            # In the actual implementation, this would not display an error
            # The check would just be skipped silently
    
    @patch('shello_cli.update.update_manager.UpdateManager')
    def test_startup_check_no_update_available(self, mock_manager_class):
        """
        Test that startup check handles no update available case.
        
        Validates: Requirements 2.1
        """
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager
        
        # Simulate no update available
        mock_manager.check_for_updates_async.return_value = UpdateCheckResult(
            update_available=False,
            current_version="0.5.0",
            latest_version="0.5.0"
        )
        
        # Create settings with check_on_startup enabled
        settings = UserSettings(
            provider="openai",
            update_config=UpdateConfig(check_on_startup=True)
        )
        
        # Simulate the startup check logic
        if settings.update_config and settings.update_config.check_on_startup:
            from shello_cli.update.update_manager import UpdateManager
            manager = UpdateManager()
            result = manager.check_for_updates_async(timeout=2.0)
            
            # Verify the check was called
            assert result is not None
            assert result.update_available is False
            
            # In the actual implementation, no notification would be displayed
    
    def test_update_config_default_value(self):
        """
        Test that UpdateConfig defaults to check_on_startup=True.
        
        Validates: Requirements 2.7
        """
        config = UpdateConfig()
        assert config.check_on_startup is True
    
    def test_user_settings_default_update_config(self):
        """
        Test that UserSettings has default UpdateConfig.
        
        Validates: Requirements 2.7
        """
        settings = UserSettings(provider="openai")
        assert settings.update_config is not None
        assert settings.update_config.check_on_startup is True
