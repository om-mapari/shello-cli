"""Integration tests for BashTool with TrustManager."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from shello_cli.tools.bash_tool import BashTool
from shello_cli.utils.settings_manager import CommandTrustConfig
from shello_cli.constants import DEFAULT_ALLOWLIST, DEFAULT_DENYLIST


class TestBashToolTrustIntegration:
    """Test BashTool integration with TrustManager."""
    
    @patch('shello_cli.utils.settings_manager.SettingsManager')
    def test_execute_with_allowlist_command(self, mock_settings_manager_class):
        """Test that allowlist commands execute without approval."""
        # Setup mock settings manager
        mock_settings_manager = Mock()
        mock_settings_manager_class.get_instance.return_value = mock_settings_manager
        
        # Configure trust settings with default allowlist
        trust_config = CommandTrustConfig(
            enabled=True,
            yolo_mode=False,
            approval_mode="user_driven",
            allowlist=DEFAULT_ALLOWLIST.copy(),
            denylist=DEFAULT_DENYLIST.copy()
        )
        mock_settings_manager.get_command_trust_config.return_value = trust_config
        
        # Execute allowlist command
        bash_tool = BashTool()
        result = bash_tool.execute("git status")
        
        # Should execute without approval
        assert result.success is True
        assert result.error is None
    
    @patch('shello_cli.utils.settings_manager.SettingsManager')
    def test_execute_with_denylist_command_denied(self, mock_settings_manager_class):
        """Test that denylist commands require approval and can be denied."""
        # Setup mock settings manager
        mock_settings_manager = Mock()
        mock_settings_manager_class.get_instance.return_value = mock_settings_manager
        
        # Configure trust settings
        trust_config = CommandTrustConfig(
            enabled=True,
            yolo_mode=False,
            approval_mode="user_driven",
            allowlist=DEFAULT_ALLOWLIST.copy(),
            denylist=DEFAULT_DENYLIST.copy()
        )
        mock_settings_manager.get_command_trust_config.return_value = trust_config
        
        # Mock approval dialog to deny
        with patch('shello_cli.trust.approval_dialog.ApprovalDialog.show', return_value=False):
            bash_tool = BashTool()
            result = bash_tool.execute("rm -rf /")
            
            # Should be denied
            assert result.success is False
            assert result.error == "Command execution denied by user"
    
    @patch('shello_cli.utils.settings_manager.SettingsManager')
    def test_execute_with_denylist_command_approved(self, mock_settings_manager_class):
        """Test that denylist commands can be approved and execute."""
        # Setup mock settings manager
        mock_settings_manager = Mock()
        mock_settings_manager_class.get_instance.return_value = mock_settings_manager
        
        # Configure trust settings
        trust_config = CommandTrustConfig(
            enabled=True,
            yolo_mode=False,
            approval_mode="user_driven",
            allowlist=DEFAULT_ALLOWLIST.copy(),
            denylist=DEFAULT_DENYLIST.copy()
        )
        mock_settings_manager.get_command_trust_config.return_value = trust_config
        
        # Mock approval dialog to approve
        with patch('shello_cli.trust.approval_dialog.ApprovalDialog.show', return_value=True):
            bash_tool = BashTool()
            # Use a safer denylist-like command for testing
            result = bash_tool.execute("echo 'test dangerous command'")
            
            # Should execute after approval
            assert result.success is True
    
    @patch('shello_cli.utils.settings_manager.SettingsManager')
    def test_execute_with_yolo_mode(self, mock_settings_manager_class):
        """Test that YOLO mode bypasses approval for non-denylist commands."""
        # Setup mock settings manager
        mock_settings_manager = Mock()
        mock_settings_manager_class.get_instance.return_value = mock_settings_manager
        
        # Configure trust settings with YOLO mode
        trust_config = CommandTrustConfig(
            enabled=True,
            yolo_mode=True,
            approval_mode="user_driven",
            allowlist=DEFAULT_ALLOWLIST.copy(),
            denylist=DEFAULT_DENYLIST.copy()
        )
        mock_settings_manager.get_command_trust_config.return_value = trust_config
        
        # Execute non-allowlist command
        bash_tool = BashTool()
        result = bash_tool.execute("echo 'test'")
        
        # Should execute without approval due to YOLO mode
        assert result.success is True
    
    @patch('shello_cli.utils.settings_manager.SettingsManager')
    def test_execute_with_ai_safe_flag_true(self, mock_settings_manager_class):
        """Test that is_safe=True in ai_driven mode allows execution."""
        # Setup mock settings manager
        mock_settings_manager = Mock()
        mock_settings_manager_class.get_instance.return_value = mock_settings_manager
        
        # Configure trust settings with ai_driven mode
        trust_config = CommandTrustConfig(
            enabled=True,
            yolo_mode=False,
            approval_mode="ai_driven",
            allowlist=DEFAULT_ALLOWLIST.copy(),
            denylist=DEFAULT_DENYLIST.copy()
        )
        mock_settings_manager.get_command_trust_config.return_value = trust_config
        
        # Execute with is_safe=True
        bash_tool = BashTool()
        result = bash_tool.execute("echo 'test'", is_safe=True)
        
        # Should execute without approval
        assert result.success is True
    
    @patch('shello_cli.utils.settings_manager.SettingsManager')
    def test_execute_with_ai_safe_flag_false(self, mock_settings_manager_class):
        """Test that is_safe=False in ai_driven mode requires approval."""
        # Setup mock settings manager
        mock_settings_manager = Mock()
        mock_settings_manager_class.get_instance.return_value = mock_settings_manager
        
        # Configure trust settings with ai_driven mode
        trust_config = CommandTrustConfig(
            enabled=True,
            yolo_mode=False,
            approval_mode="ai_driven",
            allowlist=DEFAULT_ALLOWLIST.copy(),
            denylist=DEFAULT_DENYLIST.copy()
        )
        mock_settings_manager.get_command_trust_config.return_value = trust_config
        
        # Mock approval dialog to deny
        with patch('shello_cli.trust.approval_dialog.ApprovalDialog.show', return_value=False):
            bash_tool = BashTool()
            result = bash_tool.execute("echo 'test'", is_safe=False)
            
            # Should be denied
            assert result.success is False
            assert result.error == "Command execution denied by user"
    
    @patch('shello_cli.utils.settings_manager.SettingsManager')
    def test_execute_stream_with_allowlist_command(self, mock_settings_manager_class):
        """Test that execute_stream works with allowlist commands."""
        # Setup mock settings manager
        mock_settings_manager = Mock()
        mock_settings_manager_class.get_instance.return_value = mock_settings_manager
        
        # Configure trust settings
        trust_config = CommandTrustConfig(
            enabled=True,
            yolo_mode=False,
            approval_mode="user_driven",
            allowlist=DEFAULT_ALLOWLIST.copy(),
            denylist=DEFAULT_DENYLIST.copy()
        )
        mock_settings_manager.get_command_trust_config.return_value = trust_config
        
        # Execute allowlist command with streaming
        bash_tool = BashTool()
        stream = bash_tool.execute_stream("git status")
        
        # Consume the stream - the return value is in StopIteration
        output_chunks = []
        result = None
        try:
            while True:
                chunk = next(stream)
                output_chunks.append(chunk)
        except StopIteration as e:
            result = e.value
        
        # Should execute without approval
        assert result is not None
        assert result.success is True
    
    @patch('shello_cli.utils.settings_manager.SettingsManager')
    def test_execute_stream_with_denied_command(self, mock_settings_manager_class):
        """Test that execute_stream handles denied commands."""
        # Setup mock settings manager
        mock_settings_manager = Mock()
        mock_settings_manager_class.get_instance.return_value = mock_settings_manager
        
        # Configure trust settings
        trust_config = CommandTrustConfig(
            enabled=True,
            yolo_mode=False,
            approval_mode="user_driven",
            allowlist=DEFAULT_ALLOWLIST.copy(),
            denylist=DEFAULT_DENYLIST.copy()
        )
        mock_settings_manager.get_command_trust_config.return_value = trust_config
        
        # Mock approval dialog to deny
        with patch('shello_cli.trust.approval_dialog.ApprovalDialog.show', return_value=False):
            bash_tool = BashTool()
            stream = bash_tool.execute_stream("rm -rf /")
            
            # Consume the stream - the return value is in StopIteration
            output_chunks = []
            result = None
            try:
                while True:
                    chunk = next(stream)
                    output_chunks.append(chunk)
            except StopIteration as e:
                result = e.value
            
            # Should be denied
            assert result is not None
            assert result.success is False
            assert result.error == "Command execution denied by user"
    
    @patch('shello_cli.utils.settings_manager.SettingsManager')
    def test_execute_with_trust_disabled(self, mock_settings_manager_class):
        """Test that commands execute without checks when trust is disabled."""
        # Setup mock settings manager
        mock_settings_manager = Mock()
        mock_settings_manager_class.get_instance.return_value = mock_settings_manager
        
        # Configure trust settings with trust disabled
        trust_config = CommandTrustConfig(
            enabled=False,
            yolo_mode=False,
            approval_mode="user_driven",
            allowlist=DEFAULT_ALLOWLIST.copy(),
            denylist=DEFAULT_DENYLIST.copy()
        )
        mock_settings_manager.get_command_trust_config.return_value = trust_config
        
        # Execute any command
        bash_tool = BashTool()
        result = bash_tool.execute("echo 'test'")
        
        # Should execute without any checks
        assert result.success is True
