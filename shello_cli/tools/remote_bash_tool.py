"""
Remote shell command execution tool for Shello CLI.
"""

from typing import Optional, Generator, Any
import paramiko

from shello_cli.types import ToolResult, ShelloTool
from shello_cli.tools.base import ShelloToolBase
from shello_cli.tools.output.cache import OutputCache
from shello_cli.tools.output.manager import OutputManager
from shello_cli.utils.output_utils import strip_line_padding, sanitize_surrogates


class SSHConnectionManager:
    """Manages cached SSH connections using paramiko."""
    
    _client: Optional[paramiko.SSHClient] = None

    @classmethod
    def get_client(cls) -> paramiko.SSHClient:
        """Get or create a cached SSH connection client."""
        if cls._client is not None:
            try:
                transport = cls._client.get_transport()
                if transport and transport.is_active():
                    return cls._client
            except Exception:
                pass
            cls.close()

        # Load remote server config
        from shello_cli.settings import SettingsManager
        cfg = SettingsManager.get_instance().get_remote_server_config()
        if not cfg or not cfg.host:
            raise ValueError(
                "Remote execution is not configured. "
                "Please configure remote_server settings in .shello/settings.yml or ~/.shello_cli/user-settings.yml."
            )

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        connect_kwargs = {
            "hostname": cfg.host,
            "port": cfg.port or 22,
            "username": cfg.username,
            "timeout": float(cfg.timeout or 60),
        }
        if cfg.password:
            connect_kwargs["password"] = cfg.password
        if cfg.private_key_path:
            connect_kwargs["key_filename"] = cfg.private_key_path

        client.connect(**connect_kwargs)
        cls._client = client
        return client

    @classmethod
    def close(cls) -> None:
        """Close the cached SSH client."""
        if cls._client:
            try:
                cls._client.close()
            except Exception:
                pass
            cls._client = None


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
                        "description": "Shell command to execute on the remote SSH server, or stdin input if is_input=true, or empty to poll."
                    },
                    "is_safe": {
                        "type": "boolean",
                        "description": "true=read-only (ls, cat), false=destructive (rm, dd). When unsure, use false."
                    },
                    "use_sudo": {
                        "type": "boolean",
                        "description": "Execute the command with sudo on the remote machine."
                    },
                    "is_input": {
                        "type": "boolean",
                        "description": "If true, treats command as standard input (stdin) to the active running process. Default is false."
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Max duration in seconds to wait for output. Default is 60."
                    },
                    "reset": {
                        "type": "boolean",
                        "description": "If true, terminates any active background process, clears state, and starts fresh. Default is false."
                    }
                },
                "required": ["command", "is_safe"]
            }
        }
    )

    def __init__(self, mcp_client: Optional[Any] = None, output_cache: Optional[OutputCache] = None):
        # mcp_client is kept for signature compatibility
        self._output_cache = output_cache or OutputCache()
        self._output_manager = OutputManager(cache=self._output_cache)

    @property
    def schema(self) -> ShelloTool:
        return self._SCHEMA

    def execute(self, command: str = "", is_safe: Optional[bool] = None, use_sudo: bool = False, timeout: int = 60,
                is_input: bool = False, reset: bool = False) -> ToolResult:
        # Remote SSH execution is one-shot and stateless — interactive modes are not supported
        if is_input:
            return ToolResult(
                success=False,
                output=None,
                error=(
                    "Remote interactive input (is_input=true) is not supported. "
                    "SSH exec_command is one-shot and has no persistent stdin channel. "
                    "Use command chaining instead (e.g. 'echo \"input\" | command')."
                ),
                error_type="process_control"
            )
        if reset:
            return ToolResult(
                success=True,
                output="Remote session has no persistent process state to reset.",
                error=None,
                error_type="process_control"
            )

        if not command or not command.strip():
            return ToolResult(success=False, output=None, error="No command provided")

        # 1. Get Remote Server config
        from shello_cli.settings import SettingsManager
        cfg = SettingsManager.get_instance().get_remote_server_config()
        if not cfg or not cfg.host:
            return ToolResult(
                success=False,
                output=None,
                error=(
                    "Remote execution is not configured. "
                    "Please configure remote_server settings in .shello/settings.yml or ~/.shello_cli/user-settings.yml."
                )
            )

        # 2. Evaluate command trust using TrustManager
        trust = self._evaluate_command_trust(command, is_safe)
        if not trust.success:
            return trust

        # If disable_sudo is True in the config, override use_sudo to False
        if cfg.disable_sudo:
            use_sudo = False

        # 3. Connect and execute the remote command natively
        try:
            client = SSHConnectionManager.get_client()
            
            # Wrap command for execution
            if use_sudo:
                if cfg.sudo_password:
                    pwd_escaped = cfg.sudo_password.replace("'", "'\\''")
                    cmd_escaped = command.replace("'", "'\\''")
                    wrapped = "printf '%s\\n' '{}' | sudo -p \"\" -S sh -c '{}'".format(pwd_escaped, cmd_escaped)
                else:
                    cmd_escaped = command.replace("'", "'\\''")
                    wrapped = "sudo -n sh -c '{}'".format(cmd_escaped)
            else:
                cmd_escaped = command.replace("'", "'\\''")
                wrapped = "sh -c '{}'".format(cmd_escaped)

            # Execute via paramiko
            stdin, stdout, stderr = client.exec_command(wrapped, timeout=float(timeout))
            
            # Read output and error streams
            out = stdout.read().decode('utf-8', errors='replace')
            err = stderr.read().decode('utf-8', errors='replace')
            exit_status = stdout.channel.recv_exit_status()

            output = sanitize_surrogates(out)
            error = sanitize_surrogates(err) if err else None
            output = strip_line_padding(output)

            if exit_status != 0:
                err_msg = error or output or f"Remote command failed with exit status {exit_status}"
                return ToolResult(
                    success=False,
                    output=output or None,
                    error=err_msg
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
