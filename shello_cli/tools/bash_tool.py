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


class BashTool:
    """Bash command execution tool.
    
    This tool executes bash commands in a subprocess, captures output,
    and maintains the current working directory state across commands.
    """
    
    def __init__(self):
        """Initialize the bash tool with the current working directory."""
        self._current_directory: str = os.getcwd()
        
        # Detect the actual shell being used
        self._detect_shell()
    
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
    
    def execute(self, command: str, timeout: int = 30) -> ToolResult:
        """Execute a bash command and return the result.
        
        Args:
            command: The bash command to execute
            timeout: Maximum execution time in seconds (default: 30)
        
        Returns:
            ToolResult with success status, output, and any errors
        """
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
            
            # Determine success based on return code
            if result.returncode == 0:
                # Process output through OutputManager
                from shello_cli.tools.output_manager import OutputManager
                output_manager = OutputManager.from_settings()
                
                # Process the output
                truncation_result = output_manager.process_output(output, command)
                
                # Combine output with warning if truncated
                final_output = truncation_result.output
                if truncation_result.was_truncated and truncation_result.warning:
                    final_output = truncation_result.output + truncation_result.warning
                
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
    
    def execute_stream(self, command: str, timeout: int = 30) -> Generator[str, None, ToolResult]:
        """Execute a bash command and stream output in real-time.
        
        Args:
            command: The bash command to execute
            timeout: Maximum execution time in seconds (default: 30)
        
        Yields:
            Output chunks as they arrive from the command
        
        Returns:
            ToolResult with final success status and any errors
        """
        # Handle cd commands specially to update working directory
        if command.strip().startswith('cd') and (
            command.strip() == 'cd' or command.strip().startswith('cd ')
        ):
            result = self._handle_cd_command(command)
            yield result.output or result.error or ""
            return result
        
        try:
            # Start the process based on shell type
            if self._shell_type == 'powershell':
                # Use PowerShell explicitly
                process = subprocess.Popen(
                    ['powershell.exe', '-Command', command],
                    cwd=self._current_directory,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    bufsize=1,
                    encoding='utf-8',
                    errors='replace'  # Replace invalid chars instead of failing
                )
            else:
                # Use default shell
                process = subprocess.Popen(
                    command,
                    shell=True,
                    cwd=self._current_directory,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    bufsize=1,  # Line buffered
                    encoding='utf-8',
                    errors='replace'  # Replace invalid chars instead of failing
                )
            
            accumulated_output = []
            accumulated_error = []
            
            # Create a generator for the raw output
            def raw_output_generator():
                """Generator that yields raw output from the process."""
                # Read from stdout
                if process.stdout:
                    for line in iter(process.stdout.readline, ''):
                        if line:
                            accumulated_output.append(line)
                            yield line
                
                # Wait for process to complete
                try:
                    process.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    process.kill()
                    raise
                
                # Read any remaining stderr
                if process.stderr:
                    stderr_content = process.stderr.read()
                    if stderr_content:
                        accumulated_error.append(stderr_content)
                        yield stderr_content
            
            # Wrap the raw output with OutputManager for streaming truncation
            from shello_cli.tools.output_manager import OutputManager
            output_manager = OutputManager.from_settings()
            
            # Process stream through OutputManager
            stream_wrapper = output_manager.process_stream(raw_output_generator(), command)
            
            # Yield all chunks from the wrapped stream and capture the return value
            truncation_result = None
            try:
                while True:
                    chunk = next(stream_wrapper)
                    yield chunk
            except StopIteration as e:
                # The return value is in e.value
                truncation_result = e.value
            
            # Determine success based on return code
            output = ''.join(accumulated_output)
            error = ''.join(accumulated_error)
            
            if process.returncode == 0:
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
                    error=error if error else f"Command failed with exit code {process.returncode}",
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
