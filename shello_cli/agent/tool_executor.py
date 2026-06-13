"""
Tool execution for the Shello Agent.

All dispatch goes through the registry — no hardcoded if/elif chains.
Adding a new tool only requires registering it here; nothing else changes.
"""

import json
from typing import Dict, Any, Generator

from shello_cli.types import ToolResult
from shello_cli.tools.output.cache import OutputCache
from shello_cli.tools import registry

# Module-level imports kept here so tests can patch them at this location,
# e.g. patch('shello_cli.agent.tool_executor.BashTool')
from shello_cli.tools.bash_tool import BashTool
from shello_cli.tools.json_analyzer_tool import JsonAnalyzerTool
from shello_cli.tools.get_cached_output_tool import GetCachedOutputTool
from shello_cli.tools.remote_bash_tool import RemoteBashTool


class ToolExecutor:
    """Handles execution of tools requested by the AI."""

    def __init__(self):
        self._output_cache = OutputCache()
        self._register_tools()

    def _register_tools(self) -> None:
        """Instantiate tools with the shared cache and (re-)register them.

        Clears any previously registered tools first so the agent always
        uses the single shared OutputCache instance for both execution and
        cache retrieval.

        Module-level imports (BashTool, JsonAnalyzerTool, GetCachedOutputTool)
        are used here so tests can patch them at the tool_executor module level.
        """
        # Clear the registry so we own the shared cache (tools.py may have
        # registered throw-away instances for schema-only access).
        registry._REGISTRY.clear()

        bash = BashTool(output_cache=self._output_cache)
        remote_bash = RemoteBashTool(output_cache=self._output_cache)
        registry.register(bash, name="run_shell_command")
        registry.register(JsonAnalyzerTool(bash_tool=bash), name="analyze_json")
        registry.register(GetCachedOutputTool(cache=self._output_cache), name="get_cached_output")
        registry.register(remote_bash, name="run_remote_command")

        # Store bash reference for helpers that need it directly
        self._bash_tool = bash

        # Initialize MCP client attribute
        self._mcp_client = None

        # Load and merge MCP configurations
        try:
            from shello_cli.settings.manager import SettingsManager
            settings_manager = SettingsManager.get_instance()
            user_settings = settings_manager.load_user_settings()
            project_settings = settings_manager.load_project_settings()

            merged_mcp_servers = {}
            if user_settings and hasattr(user_settings, "mcp_servers") and isinstance(user_settings.mcp_servers, dict):
                merged_mcp_servers.update(user_settings.mcp_servers)
            if project_settings and hasattr(project_settings, "mcp_servers") and isinstance(project_settings.mcp_servers, dict):
                merged_mcp_servers.update(project_settings.mcp_servers)

            # Check for first-class SSH configuration and dynamically add ssh-mcp server if not manuals
            ssh_config = settings_manager.get_ssh_config()
            if ssh_config:
                import pathlib
                repo_root = pathlib.Path(__file__).parent.parent.parent
                ssh_mcp_js = repo_root / "ssh-mcp" / "build" / "index.js"
                
                if not ssh_mcp_js.exists():
                    ssh_mcp_js = pathlib.Path.cwd() / "ssh-mcp" / "build" / "index.js"

                args = [
                    str(ssh_mcp_js.resolve()),
                    f"--host={ssh_config.host}",
                    f"--port={ssh_config.port}",
                    f"--user={ssh_config.username}",
                ]
                if ssh_config.password:
                    args.append(f"--password={ssh_config.password}")
                if ssh_config.private_key_path:
                    args.append(f"--key={ssh_config.private_key_path}")
                if ssh_config.su_password:
                    args.append(f"--suPassword={ssh_config.su_password}")
                if ssh_config.sudo_password:
                    args.append(f"--sudoPassword={ssh_config.sudo_password}")
                if ssh_config.disable_sudo:
                    args.append("--disableSudo")
                if ssh_config.timeout:
                    args.append(f"--timeout={ssh_config.timeout * 1000}")

                # Only register if user hasn't manually registered ssh-mcp under mcp_servers
                has_manual_ssh_mcp = any("ssh-mcp" in server_name for server_name in merged_mcp_servers)
                if not has_manual_ssh_mcp:
                    merged_mcp_servers["ssh-mcp-internal"] = {
                        "command": "node",
                        "args": args
                    }

            if merged_mcp_servers:
                from shello_cli.mcp import create_mcp_client, MCPToolWrapper
                self._mcp_client = create_mcp_client(merged_mcp_servers)
                
                # Inject the client into remote_bash tool so it can run remote commands
                remote_bash.set_mcp_client(self._mcp_client)
                
                for tool in self._mcp_client.tools:
                    # Skip registering the raw exec and sudo-exec tools directly to avoid LLM confusion
                    if tool.name in ("exec", "sudo-exec"):
                        continue
                    wrapper = MCPToolWrapper(self._mcp_client, tool)
                    registry.register(wrapper, name=tool.name)
        except Exception as e:
            from shello_cli.ui.ui_renderer import console
            console.print(f"\n⚠️  [yellow]Failed to initialize MCP servers: {e}[/yellow]\n")

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    def execute_tool(self, tool_call: Dict[str, Any]) -> ToolResult:
        """Execute a tool call and return the result."""
        name, kwargs, err = self._parse(tool_call)
        if err:
            return err
        return registry.dispatch(name, **kwargs)

    def execute_tool_stream(self, tool_call: Dict[str, Any]) -> Generator[str, None, ToolResult]:
        """Execute a tool call with streaming output."""
        name, kwargs, err = self._parse(tool_call)
        if err:
            return err
            yield  # make this a generator
        return (yield from registry.dispatch_stream(name, **kwargs))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse(tool_call: Dict[str, Any]):
        """Extract name + kwargs from a raw tool_call dict.

        Returns (name, kwargs, None) on success or (None, None, ToolResult) on error.
        """
        fn = tool_call.get("function", {})
        name = fn.get("name")
        try:
            kwargs = json.loads(fn.get("arguments", "{}"))
        except json.JSONDecodeError as e:
            return None, None, ToolResult(
                success=False, output=None,
                error=f"Failed to parse tool arguments: {e}"
            )
        return name, kwargs, None

    def get_current_directory(self) -> str:
        return self._bash_tool.get_current_directory()

    def clear_cache(self) -> None:
        """Clear the output cache (call on /new or session end)."""
        self._output_cache.clear()
        self.close_mcp_client()

    def close_mcp_client(self) -> None:
        """Close the MCP client and clean up background server processes."""
        if hasattr(self, "_mcp_client") and self._mcp_client is not None:
            try:
                self._mcp_client.sync_close()
            except Exception:
                pass
            self._mcp_client = None

    def __del__(self):
        try:
            self.close_mcp_client()
        except Exception:
            pass
