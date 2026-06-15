"""
Bash command execution tool for Shello CLI.
"""

import subprocess
import os
import platform
import queue
import threading
import time
from typing import Optional, Generator

from shello_cli.types import ToolResult, ShelloTool
from shello_cli.tools.base import ShelloToolBase
from shello_cli.tools.output.cache import OutputCache
from shello_cli.tools.output.manager import OutputManager
from shello_cli.tools.output.types import TruncationResult, OutputType, TruncationStrategy
from shello_cli.utils.output_utils import strip_line_padding, sanitize_surrogates
from shello_cli.utils.system_info import detect_shell


class GeneratorWrapper:
    def __init__(self, gen):
        self.gen = gen
        self.value = None

    def __iter__(self):
        return self

    def __next__(self):
        try:
            return next(self.gen)
        except StopIteration as e:
            self.value = e.value
            raise


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
                        "description": (
                            "Shell command to execute, or stdin input if is_input=true, or empty to poll. "
                            "To abort/interrupt the active background process, set command to 'C-c' with is_input=true. "
                            "To send EOF (close stdin) to the active background process, set command to 'C-d' with is_input=true."
                        )
                    },
                    "is_safe": {
                        "type": "boolean",
                        "description": "true=read-only (ls, cat), false=destructive (rm, dd). When unsure, use false."
                    },
                    "is_input": {
                        "type": "boolean",
                        "description": "If true, treats command as standard input (stdin) to the active running process. Default is false."
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Max duration in seconds to wait for output. Default is 30."
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

    def __init__(self, output_cache: Optional[OutputCache] = None):
        self._current_directory: str = os.getcwd()
        self._output_cache = output_cache or OutputCache()
        self._output_manager = OutputManager(cache=self._output_cache)
        self._shell_type, self._shell_executable = detect_shell()
        self._active_process: Optional[subprocess.Popen] = None
        self._out_queue: Optional[queue.Queue] = None
        self._reader_thread: Optional[threading.Thread] = None
        self._accumulated_output: list[str] = []
        self._active_process_command: Optional[str] = None

    @property
    def schema(self) -> ShelloTool:
        return self._SCHEMA

    # ------------------------------------------------------------------
    # ShelloToolBase interface
    # ------------------------------------------------------------------

    def execute(self, command: str = "", is_safe: Optional[bool] = None, timeout: int = 30,
                is_input: bool = False, reset: bool = False) -> ToolResult:
        wrapper = GeneratorWrapper(self._execute_generator(command, is_safe, timeout, is_input, reset))
        for _ in wrapper:
            pass
        return wrapper.value

    def execute_stream(self, command: str = "", is_safe: Optional[bool] = None,
                       timeout: int = 30, is_input: bool = False, reset: bool = False) -> Generator[str, None, ToolResult]:
        command_for_stream = command if command else getattr(self, "_active_process_command", "") or "active_process"
        wrapper = GeneratorWrapper(self._execute_generator(command, is_safe, timeout, is_input, reset))
        yield from self._output_manager.process_stream(wrapper, command_for_stream)
        return wrapper.value

    def _reset_active_process(self):
        if self._active_process:
            if self._active_process.poll() is None:
                try:
                    self._active_process.terminate()
                    self._active_process.wait(timeout=0.5)
                except Exception:
                    try:
                        self._active_process.kill()
                    except Exception:
                        pass
            self._active_process = None
        self._out_queue = None
        self._reader_thread = None
        self._accumulated_output = []
        self._active_process_command = None

    def _execute_generator(self, command: str = "", is_safe: Optional[bool] = None, timeout: int = 30,
                           is_input: bool = False, reset: bool = False) -> Generator[str, None, ToolResult]:
        if reset:
            self._reset_active_process()
            if not command or not command.strip() or command.strip().lower() in ("reset", "reset session"):
                return ToolResult(success=True, output="Session reset successfully", error=None,
                                  error_type="process_control")

        process_active = self._active_process is not None and self._active_process.poll() is None
        
        if process_active:
            if is_input:
                if command == "C-c":
                    self._reset_active_process()
                    return ToolResult(
                        success=False,
                        output=None,
                        error="Process interrupted (SIGINT)",
                        data={"exit_code": -1},
                        error_type="process_control"
                    )
                elif command == "C-d":
                    try:
                        if self._active_process.stdin:
                            self._active_process.stdin.close()
                    except Exception as e:
                        return ToolResult(
                            success=False,
                            output=None,
                            error=f"Error closing stdin: {e}",
                            data={"exit_code": -1}
                        )
                else:
                    try:
                        if self._active_process.stdin:
                            self._active_process.stdin.write(command + '\n')
                            self._active_process.stdin.flush()
                        else:
                            return ToolResult(
                                success=False,
                                output=None,
                                error="Active process stdin is not writable",
                                data={"exit_code": -1}
                            )
                    except Exception as e:
                        return ToolResult(
                            success=False,
                            output=None,
                            error=f"Error writing to process stdin: {e}",
                            data={"exit_code": -1}
                        )
            else:
                if command == "":
                    pass
                else:
                    return ToolResult(
                        success=False,
                        output=None,
                        error="A process is already running. You must complete, reset, or abort (C-c) it first, or use is_input=true to interact."
                    )
        else:
            if is_input:
                return ToolResult(
                    success=False,
                    output=None,
                    error="No active process to send input to"
                )
            if not command or not command.strip():
                return ToolResult(
                    success=False,
                    output=None,
                    error="No command provided and no active process to poll"
                )
            
            trust = self._evaluate_command_trust(command, is_safe)
            if not trust.success:
                return trust
                
            if self._is_cd(command):
                return self._handle_cd_command(command)
                
            try:
                self._active_process = self._start_process(command)
                self._active_process_command = command
                self._out_queue = queue.Queue()
                self._accumulated_output = []
                
                proc = self._active_process
                q = self._out_queue
                def _reader():
                    try:
                        while True:
                            char = proc.stdout.read(1)
                            if char:
                                q.put(char)
                            else:
                                break
                    except Exception:
                        pass
                    finally:
                        q.put(None)
                
                self._reader_thread = threading.Thread(target=_reader, daemon=True)
                self._reader_thread.start()
            except Exception as e:
                self._reset_active_process()
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"Failed to start process: {e}"
                )

        start_time = time.time()
        last_output_time = start_time
        NO_CHANGE_TIMEOUT = 10.0
        
        proc = self._active_process
        q = self._out_queue
        invocation_output = []
        timed_out = False
        timeout_reason = ""
        
        while True:
            try:
                chunk = q.get(timeout=0.05)
                if chunk is not None:
                    invocation_output.append(chunk)
                    self._accumulated_output.append(chunk)
                    yield chunk
                    last_output_time = time.time()
                else:
                    break
            except queue.Empty:
                if proc.poll() is not None:
                    while True:
                        try:
                            chunk = q.get_nowait()
                            if chunk is None:
                                break
                            invocation_output.append(chunk)
                            self._accumulated_output.append(chunk)
                            yield chunk
                        except queue.Empty:
                            break
                    break
                
                if time.time() - start_time > timeout:
                    timed_out = True
                    timeout_reason = f"Command timed out after {timeout} seconds"
                    break
                
                if time.time() - last_output_time > NO_CHANGE_TIMEOUT:
                    timed_out = True
                    timeout_reason = f"No output produced for {NO_CHANGE_TIMEOUT} seconds (soft timeout)"
                    break

        raw_output = "".join(invocation_output)
        stripped = strip_line_padding(sanitize_surrogates(raw_output))
        
        if timed_out:
            command_for_cache = self._active_process_command or "active_process"
            trunc = self._output_manager.process_output(stripped, command_for_cache)
            final_output = trunc.output
            if trunc.was_truncated and trunc.summary:
                final_output = trunc.output + '\n' + trunc.summary
            
            return ToolResult(
                success=False,
                output=final_output or None,
                error=timeout_reason,
                data={"exit_code": -1},
                truncation_info=trunc,
                error_type="soft_timeout" if "timed out after" in timeout_reason else "no_change_timeout"
            )
            
        return_code = proc.poll()
        if return_code is None:
            try:
                return_code = proc.wait(timeout=1.0)
            except Exception:
                return_code = -1
        self._reset_active_process()
        
        success = (return_code == 0)
        command_for_cache = self._active_process_command or "active_process"
        trunc = self._output_manager.process_output(stripped, command_for_cache)
        final_output = trunc.output
        if trunc.was_truncated and trunc.summary:
            final_output = trunc.output + '\n' + trunc.summary
            
        if success:
            return ToolResult(
                success=True,
                output=final_output or "Command completed successfully",
                error=None,
                data={"exit_code": return_code},
                truncation_info=trunc
            )
        else:
            return ToolResult(
                success=False,
                output=final_output or None,
                error=f"Command failed with exit code {return_code}",
                data={"exit_code": return_code},
                truncation_info=trunc
            )

    # ------------------------------------------------------------------
    # Public helpers (used by agent / tests)
    # ------------------------------------------------------------------

    def get_current_directory(self) -> str:
        return self._current_directory

    def set_current_directory(self, directory: str) -> None:
        self._current_directory = directory

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
                stdin=subprocess.PIPE,
                bufsize=0, encoding='utf-8', errors='replace'
            )
        return subprocess.Popen(
            command, shell=True,
            cwd=self._current_directory,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            stdin=subprocess.PIPE,
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
            if isinstance(approved, str):
                return ToolResult(success=False, output=None,
                                  error=f"Command execution denied by user. Feedback: {approved}")
            elif not approved:
                return ToolResult(success=False, output=None,
                                  error="Command execution denied by user")
        return ToolResult(success=True, output=None, error=None)
