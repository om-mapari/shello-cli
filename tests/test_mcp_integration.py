from unittest.mock import Mock, patch
import pytest
import tempfile
from pathlib import Path
import yaml

# Pre-import MCP modules so they are registered in sys.modules and mock.patch can resolve them
import shello_cli.mcp.utils
import shello_cli.mcp.client
import shello_cli.mcp.tool_wrapper
import shello_cli.mcp

from shello_cli.settings import SettingsManager, UserSettings, ProjectSettings
from shello_cli.agent.tool_executor import ToolExecutor
from shello_cli.types import ToolResult


def test_mcp_settings_parsing():
    """Verify that mcp_servers is parsed correctly from global and project yaml."""
    with tempfile.TemporaryDirectory() as temp_dir:
        manager = SettingsManager()
        manager._user_settings_path = Path(temp_dir) / "user-settings.yml"
        manager._project_settings_path = Path(temp_dir) / "project-settings.yml"

        # Write user settings with mcp_servers
        user_data = {
            "provider": "openai",
            "mcp_servers": {
                "fetch": {
                    "command": "uvx",
                    "args": ["mcp-server-fetch"],
                }
            },
        }
        with open(manager._user_settings_path, "w") as f:
            yaml.dump(user_data, f)

        # Write project settings with mcp_servers overriding/adding
        project_data = {
            "model": "gpt-4o",
            "mcp_servers": {
                "repomix": {
                    "command": "npx",
                    "args": ["repomix"],
                }
            },
        }
        with open(manager._project_settings_path, "w") as f:
            yaml.dump(project_data, f)

        # Force load
        manager._user_settings = None
        manager._project_settings = None

        user_settings = manager.load_user_settings()
        project_settings = manager.load_project_settings()

        assert user_settings.mcp_servers == {
            "fetch": {
                "command": "uvx",
                "args": ["mcp-server-fetch"],
            }
        }
        assert project_settings.mcp_servers == {
            "repomix": {
                "command": "npx",
                "args": ["repomix"],
            }
        }


@patch("shello_cli.mcp.utils.MCPConfig")
@patch("shello_cli.mcp.utils.MCPClient")
def test_create_mcp_client(mock_client_class, mock_config_class):
    """Test that create_mcp_client parses configuration and connects."""
    from shello_cli.mcp.utils import create_mcp_client

    mock_client = Mock()
    mock_client_class.return_value = mock_client

    mcp_config = {
        "fetch": {
            "command": "uvx",
            "args": ["mcp-server-fetch"],
        }
    }

    client = create_mcp_client(mcp_config)
    assert client == mock_client
    mock_client.call_async_from_sync.assert_called_once()


def test_tool_wrapper_schema_and_execute():
    """Verify that MCPToolWrapper correctly exposes schema and runs execute."""
    from shello_cli.mcp.tool_wrapper import MCPToolWrapper

    mock_client = Mock()
    mock_tool = Mock()
    mock_tool.name = "my_mcp_tool"
    mock_tool.description = "Test description"
    mock_tool.inputSchema = {
        "type": "object",
        "properties": {"query": {"type": "string"}},
    }

    wrapper = MCPToolWrapper(mock_client, mock_tool)

    # Test schema
    schema = wrapper.schema
    assert schema.type == "function"
    assert schema.function["name"] == "my_mcp_tool"
    assert schema.function["description"] == "Test description"
    assert schema.function["parameters"] == mock_tool.inputSchema

    # Test execute success
    mock_result = Mock()
    mock_result.isError = False
    mock_block = Mock()
    mock_block.text = "Hello result!"
    mock_result.content = [mock_block]
    mock_client.call_async_from_sync.return_value = mock_result

    res = wrapper.execute(query="test")
    assert isinstance(res, ToolResult)
    assert res.success is True
    assert res.output == "Hello result!"
    assert res.error is None

    # Test execute error
    mock_result_err = Mock()
    mock_result_err.isError = True
    mock_block_err = Mock()
    mock_block_err.text = "Error occurred"
    mock_result_err.content = [mock_block_err]
    mock_client.call_async_from_sync.return_value = mock_result_err

    res = wrapper.execute(query="test")
    assert res.success is False
    assert res.output is None
    assert res.error == "Error occurred"


@pytest.mark.no_mock_settings
@patch("shello_cli.settings.manager.SettingsManager.load_project_settings")
@patch("shello_cli.settings.manager.SettingsManager.load_user_settings")
@patch("shello_cli.mcp.create_mcp_client")
def test_tool_executor_registration(
    mock_create_mcp_client, mock_load_user_settings, mock_load_project_settings
):
    """Test that ToolExecutor merges configs, registers MCP tools, and cleans up."""
    # Setup mock user and project settings
    user_settings = UserSettings(
        mcp_servers={"fetch": {"command": "uvx", "args": ["fetch"]}}
    )
    project_settings = ProjectSettings(
        mcp_servers={"repomix": {"command": "npx", "args": ["repomix"]}}
    )
    mock_load_user_settings.return_value = user_settings
    mock_load_project_settings.return_value = project_settings

    # Setup mock MCP client and tools
    mock_client = Mock()
    mock_tool = Mock()
    mock_tool.name = "test_mcp_tool"
    mock_tool.description = "desc"
    mock_tool.inputSchema = {"type": "object"}
    mock_client.tools = [mock_tool]
    mock_create_mcp_client.return_value = mock_client

    from shello_cli.tools import registry

    # Clear registry before test
    registry._REGISTRY.clear()

    executor = ToolExecutor()

    # Check merged config was passed to create_mcp_client
    mock_create_mcp_client.assert_called_once_with(
        {
            "fetch": {"command": "uvx", "args": ["fetch"]},
            "repomix": {"command": "npx", "args": ["repomix"]},
        }
    )

    # Verify the tool was registered
    assert "test_mcp_tool" in registry._REGISTRY

    # Clear cache should close client
    executor.clear_cache()
    mock_client.sync_close.assert_called_once()

    # Restore default tools to avoid side-effects on other tests
    registry._REGISTRY.clear()
    from shello_cli.tools.tools import _ensure_registered
    _ensure_registered()
