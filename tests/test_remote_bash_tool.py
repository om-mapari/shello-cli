from unittest.mock import Mock, patch
import pytest
import tempfile
from pathlib import Path
import yaml

from shello_cli.settings import SettingsManager, UserSettings, ProjectSettings, SSHConfig
from shello_cli.tools.remote_bash_tool import RemoteBashTool
from shello_cli.types import ToolResult


def test_ssh_settings_parsing_and_merging():
    """Verify that SSH configuration is parsed and merged correctly from global and project settings."""
    with tempfile.TemporaryDirectory() as temp_dir:
        manager = SettingsManager()
        manager._user_settings_path = Path(temp_dir) / "user-settings.yml"
        manager._project_settings_path = Path(temp_dir) / "project-settings.yml"

        # Write user settings with ssh config
        user_data = {
            "provider": "openai",
            "ssh": {
                "host": "192.168.1.1",
                "port": 2222,
                "username": "user1",
                "password": "userpass",
                "timeout": 30
            }
        }
        with open(manager._user_settings_path, "w") as f:
            yaml.dump(user_data, f)

        # Write project settings with overriding ssh config
        project_data = {
            "ssh": {
                "host": "10.0.0.1",
                "username": "projuser",
                "sudo_password": "sudopassword"
            }
        }
        with open(manager._project_settings_path, "w") as f:
            yaml.dump(project_data, f)

        # Force load
        manager._user_settings = None
        manager._project_settings = None

        ssh_cfg = manager.get_ssh_config()
        
        assert ssh_cfg is not None
        # Project settings overrides
        assert ssh_cfg.host == "10.0.0.1"
        assert ssh_cfg.username == "projuser"
        assert ssh_cfg.sudo_password == "sudopassword"
        # Inherited from user settings
        assert ssh_cfg.port == 2222
        assert ssh_cfg.password == "userpass"
        assert ssh_cfg.timeout == 30
        assert ssh_cfg.disable_sudo is False


def test_remote_bash_tool_schema():
    """Verify that RemoteBashTool has correct schema definitions."""
    tool = RemoteBashTool()
    schema = tool.schema
    
    assert schema.type == "function"
    assert schema.function["name"] == "run_remote_command"
    assert "command" in schema.function["parameters"]["properties"]
    assert "is_safe" in schema.function["parameters"]["properties"]
    assert "use_sudo" in schema.function["parameters"]["properties"]
    assert schema.function["parameters"]["required"] == ["command", "is_safe"]


def test_remote_bash_tool_no_mcp_client():
    """Test that RemoteBashTool returns error if MCP client is not configured."""
    tool = RemoteBashTool(mcp_client=None)
    result = tool.execute(command="ls", is_safe=True)
    
    assert result.success is False
    assert "Remote execution is not configured" in result.error


@patch("shello_cli.settings.SettingsManager")
def test_remote_bash_tool_trust_denied(mock_settings_manager_class):
    """Verify that command execution is blocked when trust manager denies approval."""
    # Mock settings manager
    mock_settings_manager = Mock()
    mock_settings_manager_class.get_instance.return_value = mock_settings_manager
    
    # Configure trust config
    mock_trust_config = Mock()
    mock_trust_config.enabled = True
    mock_trust_config.yolo_mode = False
    mock_trust_config.approval_mode = "user_driven"
    mock_trust_config.allowlist = []
    mock_trust_config.denylist = []
    mock_settings_manager.get_command_trust_config.return_value = mock_trust_config
    
    # Mock SSH config to return a host so the tool executes
    ssh_cfg = SSHConfig(host="test-host")
    mock_settings_manager.get_ssh_config.return_value = ssh_cfg

    # Mock TrustManager evaluate and handle_approval_dialog
    with patch("shello_cli.trust.trust_manager.TrustManager.evaluate") as mock_eval, \
         patch("shello_cli.trust.trust_manager.TrustManager.handle_approval_dialog") as mock_dialog:
        
        eval_result = Mock()
        eval_result.requires_approval = True
        eval_result.warning_message = "Dangerous command"
        mock_eval.return_value = eval_result
        
        # User denies the dialog
        mock_dialog.return_value = False

        mcp_client = Mock()
        tool = RemoteBashTool(mcp_client=mcp_client)
        result = tool.execute(command="rm -rf /", is_safe=False)

        assert result.success is False
        assert "execution denied" in result.error
        mcp_client.call_async_from_sync.assert_not_called()


@patch("shello_cli.settings.SettingsManager")
def test_remote_bash_tool_execute_success(mock_settings_manager_class):
    """Test successful remote command execution and output caching."""
    # Mock SettingsManager
    mock_settings_manager = Mock()
    mock_settings_manager_class.get_instance.return_value = mock_settings_manager
    
    ssh_cfg = SSHConfig(host="test-host")
    mock_settings_manager.get_ssh_config.return_value = ssh_cfg

    # Mock TrustManager evaluation (allow execution)
    with patch("shello_cli.trust.trust_manager.TrustManager.evaluate") as mock_eval:
        eval_result = Mock()
        eval_result.requires_approval = False
        mock_eval.return_value = eval_result

        # Mock MCP tool execution response
        mcp_client = Mock()
        mock_mcp_result = Mock()
        mock_mcp_result.isError = False
        mock_block = Mock()
        mock_block.text = "remote file list"
        mock_mcp_result.content = [mock_block]
        mcp_client.call_async_from_sync.return_value = mock_mcp_result

        tool = RemoteBashTool(mcp_client=mcp_client)
        result = tool.execute(command="ls -la", is_safe=True)

        assert result.success is True
        assert result.output == "remote file list"
        assert result.error is None
        
        # Check that exec tool was called on mcp client
        mcp_client.call_async_from_sync.assert_called_once()
        call_args = mcp_client.call_async_from_sync.call_args[1]
        assert call_args["name"] == "exec"
        assert call_args["arguments"] == {"command": "ls -la"}


@patch("shello_cli.settings.SettingsManager")
def test_remote_bash_tool_execute_sudo_success(mock_settings_manager_class):
    """Test remote command execution with sudo option."""
    # Mock SettingsManager
    mock_settings_manager = Mock()
    mock_settings_manager_class.get_instance.return_value = mock_settings_manager
    
    ssh_cfg = SSHConfig(host="test-host")
    mock_settings_manager.get_ssh_config.return_value = ssh_cfg

    with patch("shello_cli.trust.trust_manager.TrustManager.evaluate") as mock_eval:
        eval_result = Mock()
        eval_result.requires_approval = False
        mock_eval.return_value = eval_result

        mcp_client = Mock()
        mock_mcp_result = Mock()
        mock_mcp_result.isError = False
        mock_block = Mock()
        mock_block.text = "root operations output"
        mock_mcp_result.content = [mock_block]
        mcp_client.call_async_from_sync.return_value = mock_mcp_result

        tool = RemoteBashTool(mcp_client=mcp_client)
        result = tool.execute(command="systemctl restart nginx", is_safe=False, use_sudo=True)

        assert result.success is True
        assert result.output == "root operations output"
        
        # Verify sudo-exec was called on the MCP server
        mcp_client.call_async_from_sync.assert_called_once()
        call_args = mcp_client.call_async_from_sync.call_args[1]
        assert call_args["name"] == "sudo-exec"
        assert call_args["arguments"] == {"command": "systemctl restart nginx"}
