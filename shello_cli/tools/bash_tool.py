"""
Bash command execution tool for Shello CLI.

This module provides the BashTool class for executing shell commands
and managing the current working directory.
"""

import subprocess
import os
from typing import Optional
from shello_cli.types import ToolResult


class BashTool:
    """Bash command execution tool.
    
    This tool executes bash commands in a subprocess, captures output,
    and maintains the current working directory state across commands.
    """
    
    def __init__(self):
        """Initialize the bash tool with the current working directory."""
        self._current_directory: str = os.getcwd()
    
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
            # Execute the command in the current working directory
            result = subprocess.run(
                command,
                shell=True,
                cwd=self._current_directory,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            # Combine stdout and stderr for output
            output = result.stdout
            error = result.stderr
            
            # Determine success based on return code
            if result.returncode == 0:
                return ToolResult(
                    success=True,
                    output=output if output else "Command completed successfully",
                    error=None
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
