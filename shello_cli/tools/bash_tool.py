"""
Bash command execution tool for Shello CLI.

This module provides the BashTool class for executing shell commands
and managing the current working directory.
"""

import subprocess
import os
import platform
from typing import Optional, Generator
from shello_cli.types import ToolResult
from shello_cli.tools.output.cache import OutputCache
from shello_cli.tools.output.manager import OutputManager
from shello_cli.utils.output_utils import strip_line_padding


class BashTool:
    """Bash command execution tool.
    
    This tool executes bash commands in a subprocess, captures output,
    and maintains the current working directory state across commands.
    """
    
    def __init__(self, output_cache: Optional[OutputCache] = None):
        """Initialize the bash tool with the current working directory.
        
        Args:
            output_cache: Optional shared OutputCache instance. If None, creates a new one.
        """
        self._current_directory: str = os.getcwd()
        
        # Create or use shared OutputCache
        self._output_cache = output_cache or OutputCache()
        
        # Create OutputManager with shared cache
        self._output_manager = OutputManager(cache=self._output_cache)
        
        # Detect the actual shell being used
        self._detect_shell()
    
    def _evaluate_command_trust(self, command: str, is_safe: Optional[bool] = None) -> ToolResult:
        """Evaluate command safety using TrustManager.
        
        Args:
            command: The command to evaluate
            is_safe: Optional AI safety flag
            
        Returns:
            ToolResult with success=True if command should execute,
            or success=False with error message if command was denied
        """
        from shello_cli.utils.settings_manager import SettingsManager
        from shello_cli.trust.trust_manager import TrustManager, TrustConfig
        
        # Get trust configuration from settings
        settings_manager = SettingsManager.get_instance()
        trust_config_data = settings_manager.get_command_trust_config()
        
        # Convert CommandTrustConfig to TrustConfig
        trust_config = TrustConfig(
            enabled=trust_config_data.enabled,
            yolo_mode=trust_config_data.yolo_mode,
            approval_mode=trust_config_data.approval_mode,
            allowlist=trust_config_data.allowlist,
            denylist=trust_config_data.denylist
        )
        
        # Create TrustManager and evaluate command
        trust_manager = TrustManager(trust_config)
        eval_result = trust_manager.evaluate(
            command=command,
            is_safe=is_safe,
            current_directory=self._current_directory
        )
        
        # If approval is required, show dialog
        if eval_result.requires_approval:
            approved = trust_manager.handle_approval_dialog(
                command=command,
                warning_message=eval_result.warning_message,
                current_directory=self._current_directory
            )
            
            if not approved:
                return ToolResult(
                    success=False,
                    output=None,
                    error="Command execution denied by user"
                )
        
        # Command approved or doesn't require approval
        return ToolResult(success=True, output=None, error=None)
    
    def _detect_shell(self):
        """Detect which shell to use for command execution."""
        os_name = platform.system()
        
        if os_name == 'Windows':
            # Check for bash first (Git Bash, WSL, etc.)
            # Git Bash sets BASH or BASH_VERSION environment variables
            if os.environ.get('BASH') or os.environ.get('BASH_VERSION'):
                # Use bash
                self._shell_type = 'bash'
                self._shell_executable = None  # Use shell=True default
            # Check SHELL environment variable for bash (Git Bash on Windows)
            # Also check SHLVL which is set by bash but not cmd/PowerShell
            elif (os.environ.get('SHELL') and 'bash' in os.environ.get('SHELL', '').lower()) or \
                 os.environ.get('SHLVL'):
                # Use bash
                self._shell_type = 'bash'
                self._shell_executable = None  # Use shell=True default
            # Check if running in PowerShell (but not if bash is present)
            # PSExecutionPolicyPreference is only set when actually running in PowerShell
            elif os.environ.get('PSExecutionPolicyPreference') or \
                 (os.environ.get('PSModulePath') and not os.environ.get('PROMPT', '').startswith('$P$G')):
                # Use PowerShell
                self._shell_type = 'powershell'
                self._shell_executable = 'powershell.exe'
            else:
                # Use cmd
                self._shell_type = 'cmd'
                self._shell_executable = None  # Use shell=True default
        else:
            # Unix-like systems
            self._shell_type = 'bash'
            self._shell_executable = None  # Use shell=True default
    
    def execute(self, command: str, timeout: int = 30, is_safe: Optional[bool] = None) -> ToolResult:
        """Execute a bash command and return the result.
        
        Args:
            command: The bash command to execute
            timeout: Maximum execution time in seconds (default: 30)
            is_safe: Optional AI safety flag indicating if command is safe
        
        Returns:
            ToolResult with success status, output, and any errors
        """
        # Evaluate command safety with TrustManager
        trust_result = self._evaluate_command_trust(command, is_safe)
        if not trust_result.success:
            return trust_result
        
        # Handle cd commands specially to update working directory
        if command.strip().startswith('cd') and (
            command.strip() == 'cd' or command.strip().startswith('cd ')
        ):
            return self._handle_cd_command(command)
        
        try:
            # Execute the command based on shell type
            if self._shell_type == 'powershell':
                # Use PowerShell explicitly
                result = subprocess.run(
                    ['powershell.exe', '-Command', command],
                    cwd=self._current_directory,
                    capture_output=True,
                    timeout=timeout,
                    encoding='utf-8',
                    errors='replace'  # Replace invalid chars instead of failing
                )
            else:
                # Use default shell (cmd on Windows, bash on Unix)
                result = subprocess.run(
                    command,
                    shell=True,
                    cwd=self._current_directory,
                    capture_output=True,
                    timeout=timeout,
                    encoding='utf-8',
                    errors='replace'  # Replace invalid chars instead of failing
                )
            
            # Combine stdout and stderr for output
            output = result.stdout
            error = result.stderr
            
            # Strip trailing whitespace from each line (removes PowerShell padding)
            # This preserves structure but removes unnecessary spaces that inflate char counts
            output = strip_line_padding(output)
            
            # Determine success based on return code
            if result.returncode == 0:
                # Process output through new OutputManager
                truncation_result = self._output_manager.process_output(output, command)
                
                # Combine output with summary if truncated
                final_output = truncation_result.output
                if truncation_result.was_truncated and truncation_result.summary:
                    final_output = truncation_result.output + '\n' + truncation_result.summary
                
                return ToolResult(
                    success=True,
                    output=final_output if final_output else "Command completed successfully",
                    error=None,
                    truncation_info=truncation_result
                )
            else:
                return ToolResult(
                    success=False,
                    output=output if output else None,
                    error=error if error else f"Command failed with exit code {result.returncode}"
                )
        
        except subprocess.TimeoutExpired:
            return ToolResult(
                success=False,
                output=None,
                error=f"Command timed out after {timeout} seconds"
            )
        
        except Exception as e:
            return ToolResult(
                success=False,
                output=None,
                error=f"Error executing command: {str(e)}"
            )
    
    def _handle_cd_command(self, command: str) -> ToolResult:
        """Handle cd command to change working directory.
        
        Args:
            command: The cd command to execute
        
        Returns:
            ToolResult indicating success or failure of directory change
        """
        # Extract the target directory from the command
        parts = command.strip().split(maxsplit=1)
        
        if len(parts) == 1:
            # cd with no arguments goes to home directory
            target_dir = os.path.expanduser('~')
        else:
            target_dir = parts[1].strip()
            # Expand ~ and environment variables
            target_dir = os.path.expanduser(target_dir)
            target_dir = os.path.expandvars(target_dir)
        
        # Resolve relative paths based on current directory
        if not os.path.isabs(target_dir):
            target_dir = os.path.join(self._current_directory, target_dir)
        
        # Normalize the path
        target_dir = os.path.normpath(target_dir)
        
        # Check if directory exists
        if not os.path.exists(target_dir):
            return ToolResult(
                success=False,
                output=None,
                error=f"cd: {target_dir}: No such file or directory"
            )
        
        if not os.path.isdir(target_dir):
            return ToolResult(
                success=False,
                output=None,
                error=f"cd: {target_dir}: Not a directory"
            )
        
        # Update the current directory
        self._current_directory = target_dir
        
        return ToolResult(
            success=True,
            output=f"Changed directory to {target_dir}",
            error=None
        )
    
    def get_current_directory(self) -> str:
        """Get the current working directory.
        
        Returns:
            The current working directory path
        """
        return self._current_directory
    
    def get_output_cache(self) -> OutputCache:
        """Get the shared OutputCache instance.
        
        Returns:
            The OutputCache instance used by this BashTool
        """
        return self._output_cache
    
    def execute_stream(self, command: str, timeout: int = 30, is_safe: Optional[bool] = None) -> Generator[str, None, ToolResult]:
        """Execute a bash command and stream output in real-time.
        
        Args:
            command: The bash command to execute
            timeout: Maximum execution time in seconds (default: 30)
            is_safe: Optional AI safety flag indicating if command is safe
        
        Yields:
            Output chunks as they arrive from the command
        
        Returns:
            ToolResult with final success status and any errors
        """
        # Evaluate command safety with TrustManager
        trust_result = self._evaluate_command_trust(command, is_safe)
        if not trust_result.success:
            # Yield the error message and return the result
            yield trust_result.error or "Command execution denied"
            return trust_result
        
        # Handle cd commands specially to update working directory
        if command.strip().startswith('cd') and (
            command.strip() == 'cd' or command.strip().startswith('cd ')
        ):
            result = self._handle_cd_command(command)
            yield result.output or result.error or ""
            return result
        
        try:
            import sys
            import threading
            import queue
            
            # Start the process based on shell type
            if self._shell_type == 'powershell':
                # Use PowerShell explicitly
                process = subprocess.Popen(
                    ['powershell.exe', '-Command', command],
                    cwd=self._current_directory,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,  # Merge stderr into stdout for real-time output
                    bufsize=0,  # Unbuffered
                    encoding='utf-8',
                    errors='replace'
                )
            else:
                # Use default shell
                process = subprocess.Popen(
                    command,
                    shell=True,
                    cwd=self._current_directory,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,  # Merge stderr into stdout for real-time output
                    bufsize=0,  # Unbuffered
                    encoding='utf-8',
                    errors='replace'
                )
            
            accumulated_output = []
            output_queue = queue.Queue()
            
            def reader_thread():
                """Thread to read output without blocking."""
                try:
                    while True:
                        line = process.stdout.readline()
                        if line:
                            output_queue.put(line)
                        elif process.poll() is not None:
                            break
                except Exception:
                    pass
                finally:
                    output_queue.put(None)  # Signal end
            
            # Start reader thread
            thread = threading.Thread(target=reader_thread, daemon=True)
            thread.start()
            
            # Create a generator for the raw output
            def raw_output_generator():
                """Generator that yields raw output from the process."""
                while True:
                    try:
                        # Wait for output with timeout
                        line = output_queue.get(timeout=0.1)
                        if line is None:
                            break
                        accumulated_output.append(line)
                        yield line
                    except queue.Empty:
                        # Check if process is still running
                        if process.poll() is not None:
                            # Process finished, drain remaining output
                            while True:
                                try:
                                    line = output_queue.get_nowait()
                                    if line is None:
                                        break
                                    accumulated_output.append(line)
                                    yield line
                                except queue.Empty:
                                    break
                            break
                
                # Wait for thread to finish
                thread.join(timeout=1)
            
            # Wrap the raw output with new OutputManager for streaming
            stream_wrapper = self._output_manager.process_stream(raw_output_generator(), command)
            
            # Yield all chunks from the wrapped stream
            for chunk in stream_wrapper:
                yield chunk
            
            # Get the full output for the result
            output = ''.join(accumulated_output)
            
            # Strip trailing whitespace from each line (removes PowerShell padding)
            # This must match what process_output does to ensure consistent char counts
            output = strip_line_padding(output)
            
            # NOTE: Do NOT call process_output() again here!
            # process_stream() already calls process_output() internally at the end of the stream.
            # Calling it again would cause double-caching and skip cache IDs.
            # Instead, we get the truncation info from the cache using the last stored entry.
            
            # Get truncation info from the most recent cache entry
            # The cache stores the result, so we can retrieve stats
            cache_stats = self._output_cache.get_stats()
            last_cache_id = f"cmd_{cache_stats['next_id'] - 1:03d}" if cache_stats['next_id'] > 1 else None
            
            # Create a minimal truncation result for the return value
            from .output.types import TruncationResult, OutputType, TruncationStrategy
            truncation_result = TruncationResult(
                output=output,
                was_truncated=False,
                total_chars=len(output),
                shown_chars=len(output),
                total_lines=output.count('\n') + 1,
                shown_lines=output.count('\n') + 1,
                output_type=OutputType.DEFAULT,
                strategy=TruncationStrategy.FIRST_LAST,
                cache_id=last_cache_id,
                summary=""
            )
            
            # Determine success based on return code
            if process.returncode == 0 or process.returncode is None:
                return ToolResult(
                    success=True,
                    output=output if output else "Command completed successfully",
                    error=None,
                    truncation_info=truncation_result
                )
            else:
                return ToolResult(
                    success=False,
                    output=output if output else None,
                    error=f"Command failed with exit code {process.returncode}",
                    truncation_info=truncation_result
                )
        
        except subprocess.TimeoutExpired:
            return ToolResult(
                success=False,
                output=''.join(accumulated_output) if accumulated_output else None,
                error=f"Command timed out after {timeout} seconds"
            )
        
        except Exception as e:
            return ToolResult(
                success=False,
                output=None,
                error=f"Error executing command: {str(e)}"
            )
