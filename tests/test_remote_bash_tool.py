from unittest.mock import Mock, patch
import pytest
import tempfile
from pathlib import Path
import yaml

from shello_cli.settings import SettingsManager, UserSettings, ProjectSettings, RemoteServerConfig
from shello_cli.tools.remote_bash_tool import RemoteBashTool
from shello_cli.types import ToolResult


def test_remote_server_settings_parsing_and_merging():
    """Verify that Remote Server configuration is parsed and merged correctly from global and project settings."""
    with tempfile.TemporaryDirectory() as temp_dir:
        manager = SettingsManager()
        manager._user_settings_path = Path(temp_dir) / "user-settings.yml"
        manager._project_settings_path = Path(temp_dir) / "project-settings.yml"

        # Write user settings with remote_server config
        user_data = {
            "provider": "openai",
            "remote_server": {
                "host": "192.168.1.1",
                "port": 2222,
                "username": "user1",
                "password": "userpass",
                "timeout": 30
            }
        }
        with open(manager._user_settings_path, "w") as f:
            yaml.dump(user_data, f)

        # Write project settings with overriding remote_server config
        project_data = {
            "remote_server": {
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

        cfg = manager.get_remote_server_config()
        
        # Project settings overrides
        assert cfg is not None
        assert cfg.host == "10.0.0.1"
        assert cfg.username == "projuser"
        assert cfg.sudo_password == "sudopassword"
        # Inherited from user settings
        assert cfg.port == 2222
        assert cfg.password == "userpass"
        assert cfg.timeout == 30
        assert cfg.disable_sudo is False


def test_remote_server_settings_hyphenated_ignored():
    """Verify that hyphenated 'remote-server' config block is ignored and does not configure the remote server."""
    with tempfile.TemporaryDirectory() as temp_dir:
        manager = SettingsManager()
        manager._user_settings_path = Path(temp_dir) / "user-settings.yml"
        manager._project_settings_path = Path(temp_dir) / "project-settings.yml"

        # Write user settings with hyphenated config
        user_data = {
            "provider": "openai",
            "remote-server": {
                "host": "192.168.1.1",
                "port": 2222,
                "username": "user1",
                "password": "userpass",
                "timeout": 30
            }
        }
        with open(manager._user_settings_path, "w") as f:
            yaml.dump(user_data, f)

        # Force load
        manager._user_settings = None
        manager._project_settings = None

        cfg = manager.get_remote_server_config()
        
        # Should be None because 'remote-server' key is ignored
        assert cfg is None


def test_remote_server_settings_legacy_ssh_ignored():
    """Verify that legacy 'ssh' config block is ignored and does not configure the remote server."""
    with tempfile.TemporaryDirectory() as temp_dir:
        manager = SettingsManager()
        manager._user_settings_path = Path(temp_dir) / "user-settings.yml"
        manager._project_settings_path = Path(temp_dir) / "project-settings.yml"

        # Write user settings with legacy 'ssh' config
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

        # Force load
        manager._user_settings = None
        manager._project_settings = None

        cfg = manager.get_remote_server_config()
        
        # Should be None because 'ssh' key is ignored
        assert cfg is None


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


@patch("shello_cli.settings.SettingsManager")
def test_remote_bash_tool_not_configured(mock_settings_manager_class):
    """Test that RemoteBashTool returns error if Remote Server is not configured."""
    mock_settings_manager = Mock()
    mock_settings_manager_class.get_instance.return_value = mock_settings_manager
    mock_settings_manager.get_remote_server_config.return_value = None
    
    mock_trust_config = Mock()
    mock_trust_config.enabled = True
    mock_trust_config.yolo_mode = False
    mock_trust_config.approval_mode = "user_driven"
    mock_trust_config.allowlist = []
    mock_trust_config.denylist = []
    mock_settings_manager.get_command_trust_config.return_value = mock_trust_config

    tool = RemoteBashTool()
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
    
    # Mock config
    cfg = RemoteServerConfig(host="test-host")
    mock_settings_manager.get_remote_server_config.return_value = cfg

    # Mock TrustManager evaluate and handle_approval_dialog
    with patch("shello_cli.trust.trust_manager.TrustManager.evaluate") as mock_eval, \
         patch("shello_cli.trust.trust_manager.TrustManager.handle_approval_dialog") as mock_dialog:
        
        eval_result = Mock()
        eval_result.requires_approval = True
        eval_result.warning_message = "Dangerous command"
        mock_eval.return_value = eval_result
        
        # User denies the dialog
        mock_dialog.return_value = False

        with patch("shello_cli.tools.remote_bash_tool.SSHConnectionManager.get_client") as mock_get_client:
            tool = RemoteBashTool()
            result = tool.execute(command="rm -rf /", is_safe=False)

            assert result.success is False
            assert "execution denied" in result.error
            mock_get_client.assert_not_called()


@patch("shello_cli.settings.SettingsManager")
@patch("shello_cli.tools.remote_bash_tool.SSHConnectionManager.get_client")
def test_remote_bash_tool_execute_success(mock_get_client, mock_settings_manager_class):
    """Test successful remote command execution and output caching."""
    # Mock SettingsManager
    mock_settings_manager = Mock()
    mock_settings_manager_class.get_instance.return_value = mock_settings_manager
    
    cfg = RemoteServerConfig(host="test-host")
    mock_settings_manager.get_remote_server_config.return_value = cfg

    # Mock TrustManager evaluation (allow execution)
    with patch("shello_cli.trust.trust_manager.TrustManager.evaluate") as mock_eval:
        eval_result = Mock()
        eval_result.requires_approval = False
        mock_eval.return_value = eval_result

        # Mock paramiko client exec_command
        mock_client = Mock()
        mock_stdin = Mock()
        mock_stdout = Mock()
        mock_stderr = Mock()
        
        mock_stdout.read.return_value = b"remote file list"
        mock_stderr.read.return_value = b""
        mock_stdout.channel.recv_exit_status.return_value = 0
        
        mock_client.exec_command.return_value = (mock_stdin, mock_stdout, mock_stderr)
        mock_get_client.return_value = mock_client

        tool = RemoteBashTool()
        result = tool.execute(command="ls -la", is_safe=True)

        assert result.success is True
        assert result.output == "remote file list"
        assert result.error is None
        
        # Check that command was wrapped and executed via paramiko client
        mock_client.exec_command.assert_called_once_with("sh -c 'ls -la'", timeout=60.0)


@patch("shello_cli.settings.SettingsManager")
@patch("shello_cli.tools.remote_bash_tool.SSHConnectionManager.get_client")
def test_remote_bash_tool_execute_sudo_success(mock_get_client, mock_settings_manager_class):
    """Test remote command execution with sudo option."""
    # Mock SettingsManager
    mock_settings_manager = Mock()
    mock_settings_manager_class.get_instance.return_value = mock_settings_manager
    
    cfg = RemoteServerConfig(host="test-host", sudo_password="sudopassword")
    mock_settings_manager.get_remote_server_config.return_value = cfg

    with patch("shello_cli.trust.trust_manager.TrustManager.evaluate") as mock_eval:
        eval_result = Mock()
        eval_result.requires_approval = False
        mock_eval.return_value = eval_result

        # Mock paramiko client exec_command
        mock_client = Mock()
        mock_stdin = Mock()
        mock_stdout = Mock()
        mock_stderr = Mock()
        
        mock_stdout.read.return_value = b"root operations output"
        mock_stderr.read.return_value = b""
        mock_stdout.channel.recv_exit_status.return_value = 0
        
        mock_client.exec_command.return_value = (mock_stdin, mock_stdout, mock_stderr)
        mock_get_client.return_value = mock_client

        tool = RemoteBashTool()
        result = tool.execute(command="systemctl restart nginx", is_safe=False, use_sudo=True)

        assert result.success is True
        assert result.output == "root operations output"
        
        # Verify sudo-exec command wrapping
        mock_client.exec_command.assert_called_once_with(
            "printf '%s\\n' 'sudopassword' | sudo -p \"\" -S sh -c 'systemctl restart nginx'",
            timeout=60.0
        )
