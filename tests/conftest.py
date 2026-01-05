"""
Pytest configuration and fixtures.
"""
import pytest
from unittest.mock import Mock, patch
from hypothesis import settings

# Register Hypothesis profiles for different testing scenarios
settings.register_profile("default", max_examples=100, deadline=None)
settings.register_profile("dev", max_examples=10, deadline=None)
settings.register_profile("ci", max_examples=100, deadline=None)


@pytest.fixture(autouse=True)
def mock_settings_manager(request):
    """Mock SettingsManager to avoid slow file I/O during tests.
    
    This fixture is automatically used for all tests to prevent the
    SettingsManager from loading settings files on every BashTool creation.
    
    Tests can opt-out by using the marker: @pytest.mark.no_mock_settings
    """
    # Check if test has the no_mock_settings marker
    if 'no_mock_settings' in request.keywords:
        yield None
        return
    
    # Create mock instance
    mock_instance = Mock()
    
    # Mock get_command_trust_config to return a permissive config
    mock_trust_config = Mock()
    mock_trust_config.enabled = False  # Disable trust checks in tests
    mock_trust_config.yolo_mode = True
    mock_trust_config.approval_mode = "auto"
    mock_trust_config.allowlist = []
    mock_trust_config.denylist = []
    mock_instance.get_command_trust_config.return_value = mock_trust_config
    
    # Patch all three locations where SettingsManager might be imported
    with patch('shello_cli.utils.settings_manager.SettingsManager') as mock_settings_class_old, \
         patch('shello_cli.settings.SettingsManager') as mock_settings_class_new, \
         patch('shello_cli.settings.manager.SettingsManager') as mock_settings_class_manager:
        
        mock_settings_class_old.get_instance.return_value = mock_instance
        mock_settings_class_new.get_instance.return_value = mock_instance
        mock_settings_class_manager.get_instance.return_value = mock_instance
        
        yield mock_instance


