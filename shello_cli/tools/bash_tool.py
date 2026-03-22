"""
Bash command execution tool for Shello CLI.
"""

import subprocess
import os
import platform
import queue
import threading
from typing import Optional, Generator

from shello_cli.types import ToolResult, ShelloTool
from shello_cli.tools.base import ShelloToolBase
from shello_cli.tools.output.cache import OutputCache
from shello_cli.tools.output.manager import OutputManager
from shello_cli.tools.output.types import TruncationResult, OutputType, TruncationStrategy
from shello_cli.utils.output_utils import strip_line_padding, sanitize_surrogates


def _detect_shell() -> tuple[str, Optional[str]]:
    """Detect which shell to use. Returns (shell_type, executable_or_None)."""
    if platform.system() != 'Windows':
        return 'bash', None

    if os.environ.get('BASH') or os.environ.get('BASH_VERSION'):
        return 'bash', None
    if (os.environ.get('SHELL') and 'bash' in os.environ.get('SHELL', '').lower()) \
            or os.environ.get('SHLVL'):
        return 'bash', None
    if os.environ.get('PSExecutionPolicyPreference') or \
            (os.environ.get('PSModulePath')
             and not os.environ.get('PROMPT', '').startswith('$P$G')):
        return 'powershell', 'powershell.exe'
    return 'cmd', None


class BashTool(ShelloToolBase):
    """Shell command execution tool."""

    tool_name = "run_shell_command"

    _SCHEMA = ShelloTool(
        type="function",
        function={
            "name": "run_shell_command",
            "description": (
                "Execute a shell command on the user's machine.\n\n"
                "CRITICAL - Minimize Output:\n"
                "- ALWAYS filter at source (jq, Select-Object, findstr, head)\n"
                "- For AWS/cloud: pipe to jq for specific fields\n"
                "- For file searches: ALWAYS limit results (Select-Object -First 50, head -50)\n\n"
                "Examples:\n"
                "  ✅ aws lambda list-functions | jq '.Functions[].FunctionName'\n"
                "  ✅ Get-ChildItem -Recurse -Filter '*.py' | Select-Object -First 50\n"
                "  ✅ find . -name '*.py' -type f | head -50\n"
                "  ❌ aws lambda list-functions (dumps everything)\n"
                "  ❌ Get-ChildItem -Recurse (no limit)\n\n"
                "RULES:\n"
                "- Use shell-appropriate commands for detected OS/shell\n"
                "- Output shown to user - DON'T repeat in response\n"
                "- NEVER use echo to communicate\n"
                "- For git: use --no-pager (git --no-pager diff)\n\n"
                "SAFETY:\n"
                "- is_safe=true: read-only (dir, cat, grep) - runs immediately\n"
                "- is_safe=false: destructive (rm, dd) - needs user approval\n"
                "- Command visible to user before execution"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Shell command to execute."
                    },
                    "is_safe": {
                        "type": "boolean",
                        "description": "true=read-only (ls, cat), false=destructive (rm, dd). When unsure, use false."
                    }
                },
                "required": ["command", "is_safe"]
            }
        }
    )

    def __init__(self, output_cache: Optional[OutputCache] = None):
        self._current_directory: str = os.getcwd()
        self._output_cache = output_cache or OutputCache()
        self._output_manager = OutputManager(cache=self._output_cache)
        self._shell_type, self._shell_executable = _detect_shell()

    @property
    def schema(self) -> ShelloTool:
        return self._SCHEMA

    # ------------------------------------------------------------------
    # ShelloToolBase interface
    # ------------------------------------------------------------------

    def execute(self, command: str = "", is_safe: Optional[bool] = None, timeout: int = 30) -> ToolResult:
        if not command or not command.strip():
            return ToolResult(success=False, output=None, error="No command provided")

        trust = self._evaluate_command_trust(command, is_safe)
        if not trust.success:
            return trust

        if self._is_cd(command):
            return self._handle_cd_command(command)

        try:
            result = self._run_subprocess(command, timeout)
            output = sanitize_surrogates(result.stdout)
            error = sanitize_surrogates(result.stderr) if result.stderr else result.stderr
            output = strip_line_padding(output)

            if result.returncode == 0:
                trunc = self._output_manager.process_output(output, command)
                final = trunc.output
                if trunc.was_truncated and trunc.summary:
                    final = trunc.output + '\n' + trunc.summary
                return ToolResult(
                    success=True,
                    output=final or "Command completed successfully",
                    error=None,
                    truncation_info=trunc
                )
            else:
                return ToolResult(
                    success=False,
                    output=output or None,
                    error=error or f"Command failed with exit code {result.returncode}"
                )

        except subprocess.TimeoutExpired:
            return ToolResult(success=False, output=None,
                              error=f"Command timed out after {timeout} seconds")
        except Exception as e:
            return ToolResult(success=False, output=None,
                              error=f"Error executing command: {e}")

    def execute_stream(self, command: str = "", is_safe: Optional[bool] = None,
                       timeout: int = 30) -> Generator[str, None, ToolResult]:
        if not command or not command.strip():
            if False:
                yield
            return ToolResult(success=False, output=None, error="No command provided")

        trust = self._evaluate_command_trust(command, is_safe)
        if not trust.success:
            yield trust.error or "Command execution denied"
            return trust

        if self._is_cd(command):
            result = self._handle_cd_command(command)
            yield result.output or result.error or ""
            return result

        try:
            process = self._start_process(command)
            accumulated: list[str] = []
            out_queue: queue.Queue = queue.Queue()

            def _reader():
                try:
                    while True:
                        line = process.stdout.readline()
                        if line:
                            out_queue.put(sanitize_surrogates(line))
                        elif process.poll() is not None:
                            break
                except Exception:
                    pass
                finally:
                    out_queue.put(None)

            thread = threading.Thread(target=_reader, daemon=True)
            thread.start()

            def _raw_gen():
                while True:
                    try:
                        line = out_queue.get(timeout=0.1)
                        if line is None:
                            break
                        accumulated.append(line)
                        yield line
                    except queue.Empty:
                        if process.poll() is not None:
                            while True:
                                try:
                                    line = out_queue.get_nowait()
                                    if line is None:
                                        break
                                    accumulated.append(line)
                                    yield line
                                except queue.Empty:
                                    break
                            break
                thread.join(timeout=1)

            for chunk in self._output_manager.process_stream(_raw_gen(), command):
                yield chunk

            output = strip_line_padding(''.join(accumulated))
            cache_stats = self._output_cache.get_stats()
            last_id = f"cmd_{cache_stats['next_id'] - 1:03d}" if cache_stats['next_id'] > 1 else None
            trunc = TruncationResult(
                output=output,
                was_truncated=False,
                total_chars=len(output),
                shown_chars=len(output),
                total_lines=output.count('\n') + 1,
                shown_lines=output.count('\n') + 1,
                output_type=OutputType.DEFAULT,
                strategy=TruncationStrategy.FIRST_LAST,
                cache_id=last_id,
                summary=""
            )

            success = process.returncode in (0, None)
            return ToolResult(
                success=success,
                output=output or ("Command completed successfully" if success else None),
                error=None if success else f"Command failed with exit code {process.returncode}",
                truncation_info=trunc
            )

        except subprocess.TimeoutExpired:
            return ToolResult(success=False, output=None,
                              error=f"Command timed out after {timeout} seconds")
        except Exception as e:
            return ToolResult(success=False, output=None,
                              error=f"Error executing command: {e}")

    # ------------------------------------------------------------------
    # Public helpers (used by agent / tests)
    # ------------------------------------------------------------------

    def get_current_directory(self) -> str:
        return self._current_directory

    def get_output_cache(self) -> OutputCache:
        return self._output_cache

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _is_cd(self, command: str) -> bool:
        stripped = command.strip()
        return stripped == 'cd' or stripped.startswith('cd ')

    def _run_subprocess(self, command: str, timeout: int) -> subprocess.CompletedProcess:
        if self._shell_type == 'powershell':
            return subprocess.run(
                ['powershell.exe', '-Command', command],
                cwd=self._current_directory,
                capture_output=True, timeout=timeout,
                encoding='utf-8', errors='replace'
            )
        return subprocess.run(
            command, shell=True,
            cwd=self._current_directory,
            capture_output=True, timeout=timeout,
            encoding='utf-8', errors='replace'
        )

    def _start_process(self, command: str) -> subprocess.Popen:
        if self._shell_type == 'powershell':
            return subprocess.Popen(
                ['powershell.exe', '-Command', command],
                cwd=self._current_directory,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                bufsize=0, encoding='utf-8', errors='replace'
            )
        return subprocess.Popen(
            command, shell=True,
            cwd=self._current_directory,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            bufsize=0, encoding='utf-8', errors='replace'
        )

    def _handle_cd_command(self, command: str) -> ToolResult:
        parts = command.strip().split(maxsplit=1)
        target = os.path.expanduser('~') if len(parts) == 1 else parts[1].strip()
        target = os.path.expandvars(os.path.expanduser(target))
        if not os.path.isabs(target):
            target = os.path.join(self._current_directory, target)
        target = os.path.normpath(target)

        if not os.path.exists(target):
            return ToolResult(success=False, output=None,
                              error=f"cd: {target}: No such file or directory")
        if not os.path.isdir(target):
            return ToolResult(success=False, output=None,
                              error=f"cd: {target}: Not a directory")

        self._current_directory = target
        return ToolResult(success=True, output=f"Changed directory to {target}", error=None)

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
        eval_result = tm.evaluate(
            command=command,
            is_safe=is_safe,
            current_directory=self._current_directory
        )
        if eval_result.requires_approval:
            approved = tm.handle_approval_dialog(
                command=command,
                warning_message=eval_result.warning_message,
                current_directory=self._current_directory
            )
            if not approved:
                return ToolResult(success=False, output=None,
                                  error="Command execution denied by user")
        return ToolResult(success=True, output=None, error=None)
