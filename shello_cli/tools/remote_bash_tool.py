"""
Remote shell command execution tool for Shello CLI.
"""

from typing import Optional, Generator
from shello_cli.types import ToolResult, ShelloTool
from shello_cli.tools.base import ShelloToolBase
from shello_cli.tools.output.cache import OutputCache
from shello_cli.tools.output.manager import OutputManager
from shello_cli.tools.output.types import TruncationResult, OutputType, TruncationStrategy
from shello_cli.utils.output_utils import strip_line_padding, sanitize_surrogates


class RemoteBashTool(ShelloToolBase):
    """Remote shell command execution tool."""

    tool_name = "run_remote_command"

    _SCHEMA = ShelloTool(
        type="function",
        function={
            "name": "run_remote_command",
            "description": (
                "Execute a shell command on the remote SSH server.\n\n"
                "CRITICAL - Minimize Output:\n"
                "- ALWAYS filter at source (jq, grep, head)\n"
                "- For file searches: ALWAYS limit results\n\n"
                "RULES:\n"
                "- Output shown to user - DON'T repeat in response\n"
                "- NEVER use echo to communicate\n"
                "- Use this instead of run_shell_command when working on the remote machine.\n\n"
                "SAFETY:\n"
                "- is_safe=true: read-only (ls, cat, grep) - runs immediately\n"
                "- is_safe=false: destructive (rm, dd) - needs user approval\n"
                "- Command visible to user before execution"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Shell command to execute on the remote SSH server."
                    },
                    "is_safe": {
                        "type": "boolean",
                        "description": "true=read-only (ls, cat), false=destructive (rm, dd). When unsure, use false."
                    },
                    "use_sudo": {
                        "type": "boolean",
                        "description": "Execute the command with sudo on the remote machine."
                    }
                },
                "required": ["command", "is_safe"]
            }
        }
    )

    def __init__(self, mcp_client=None, output_cache: Optional[OutputCache] = None):
        self._mcp_client = mcp_client
        self._output_cache = output_cache or OutputCache()
        self._output_manager = OutputManager(cache=self._output_cache)

    @property
    def schema(self) -> ShelloTool:
        return self._SCHEMA

    def set_mcp_client(self, mcp_client) -> None:
        """Inject MCP client reference dynamically."""
        self._mcp_client = mcp_client

    def execute(self, command: str = "", is_safe: Optional[bool] = None, use_sudo: bool = False, timeout: int = 60) -> ToolResult:
        if not command or not command.strip():
            return ToolResult(success=False, output=None, error="No command provided")

        if not self._mcp_client:
            return ToolResult(
                success=False,
                output=None,
                error=(
                    "Remote execution is not configured. "
                    "Please configure SSH settings in .shello/settings.yml or ~/.shello_cli/user-settings.yml."
                )
            )

        # 1. Evaluate command trust using TrustManager
        trust = self._evaluate_command_trust(command, is_safe)
        if not trust.success:
            return trust

        # 2. Decide tool name (exec or sudo-exec)
        tool_name = "exec"
        from shello_cli.settings.manager import SettingsManager
        ssh_cfg = SettingsManager.get_instance().get_ssh_config()
        
        # If disable_sudo is True in the config, override use_sudo to False
        if ssh_cfg and getattr(ssh_cfg, 'disable_sudo', False):
            use_sudo = False
            
        if use_sudo:
            tool_name = "sudo-exec"

        # 3. Call the remote MCP server tool
        try:
            result = self._mcp_client.call_async_from_sync(
                self._mcp_client.call_tool_mcp,
                name=tool_name,
                arguments={"command": command},
                timeout=float(timeout),
            )

            # Build output string from content blocks
            output_parts = []
            for block in result.content:
                if hasattr(block, "text") and block.text:
                    output_parts.append(block.text)
                elif hasattr(block, "data"):
                    mime = getattr(block, "mimeType", "image/*")
                    output_parts.append(f"[Image content: {mime}]")
                else:
                    output_parts.append(str(block))

            output = sanitize_surrogates("\n".join(output_parts))
            output = strip_line_padding(output)

            is_error = getattr(result, "isError", False)
            if is_error:
                return ToolResult(
                    success=False,
                    output=output or None,
                    error=output or f"Remote command execution failed"
                )

            # 4. Truncate and cache the output
            trunc = self._output_manager.process_output(output, command)
            final = trunc.output
            if trunc.was_truncated and trunc.summary:
                final = trunc.output + '\n' + trunc.summary

            return ToolResult(
                success=True,
                output=final or "Remote command completed successfully",
                error=None,
                truncation_info=trunc
            )

        except Exception as e:
            return ToolResult(
                success=False,
                output=None,
                error=f"Error executing remote command: {e}"
            )

    def _evaluate_command_trust(self, command: str, is_safe: Optional[bool]) -> ToolResult:
        from shello_cli.settings import SettingsManager
        from shello_cli.trust.trust_manager import TrustManager, TrustConfig

        settings_manager = SettingsManager.get_instance()
        cfg = settings_manager.get_command_trust_config()
        trust_config = TrustConfig(
            enabled=cfg.enabled,
            yolo_mode=cfg.yolo_mode,
            approval_mode=cfg.approval_mode,
            allowlist=cfg.allowlist,
            denylist=cfg.denylist
        )
        tm = TrustManager(trust_config)
        
        # Evaluate trust using a generic remote path notation (we use "~")
        eval_result = tm.evaluate(
            command=command,
            is_safe=is_safe,
            current_directory="[remote] ~"
        )
        if eval_result.requires_approval:
            approved = tm.handle_approval_dialog(
                command=command,
                warning_message=eval_result.warning_message,
                current_directory="[remote] ~"
            )
            if isinstance(approved, str):
                return ToolResult(success=False, output=None,
                                  error=f"Remote command execution denied by user. Feedback: {approved}")
            elif not approved:
                return ToolResult(success=False, output=None,
                                  error="Remote command execution denied by user")
        return ToolResult(success=True, output=None, error=None)
