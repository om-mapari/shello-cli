"""
Direct command executor for Shello CLI.

This module provides the DirectExecutor class for executing shell commands
directly without AI processing, while maintaining directory state.
"""

from dataclasses import dataclass
from typing import Optional
import subprocess
import os
import platform
from shello_cli.utils.output_utils import strip_line_padding


@dataclass
class ExecutionResult:
    """Result from direct command execution.
    
    Attributes:
        success: Whether execution succeeded
        output: Command output
        error: Error message if failed
        directory_changed: Whether cd changed directory
        new_directory: New directory path if changed
        cache_id: Cache ID for the command output (if cached)
    """
    success: bool
    output: str
    error: Optional[str] = None
    directory_changed: bool = False
    new_directory: Optional[str] = None
    cache_id: Optional[str] = None


class DirectExecutor:
    """Executes direct commands without output management overhead."""
    
    def __init__(self, bash_tool=None):
        """Initialize the DirectExecutor.
        
        Args:
            bash_tool: Optional BashTool instance for caching support
        """
        self._current_directory: str = os.getcwd()
        self._bash_tool = bash_tool
        self._detect_shell()
    
    def _detect_shell(self):
        """Detect which shell to use for command execution."""
        os_name = platform.system()
        
        if os_name == 'Windows':
            # Check for bash first (Git Bash, WSL, etc.)
            if os.environ.get('BASH') or os.environ.get('BASH_VERSION'):
                self._shell_type = 'bash'
            elif (os.environ.get('SHELL') and 'bash' in os.environ.get('SHELL', '').lower()) or \
                 os.environ.get('SHLVL'):
                self._shell_type = 'bash'
            elif os.environ.get('PSExecutionPolicyPreference') or \
                 (os.environ.get('PSModulePath') and not os.environ.get('PROMPT', '').startswith('$P$G')):
                self._shell_type = 'powershell'
            else:
                self._shell_type = 'cmd'
        else:
            self._shell_type = 'bash'
    
    def _evaluate_command_trust(self, command: str, is_safe: Optional[bool] = None) -> Optional[ExecutionResult]:
        """Evaluate command safety using TrustManager.
        
        Args:
            command: The command to evaluate
            is_safe: Optional AI safety flag
            
        Returns:
            ExecutionResult with error if command was denied, None if command should execute
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
                return ExecutionResult(
                    success=False,
                    output="",
                    error="Command execution denied by user"
                )
        
        # Command approved or doesn't require approval
        return None
    
    def execute(self, command: str, args: Optional[str] = None, is_safe: Optional[bool] = None) -> ExecutionResult:
        """Execute a direct command and return the result.
        
        Args:
            command: The command to execute (e.g., 'ls', 'cd', 'pwd')
            args: Optional arguments for the command
            is_safe: Optional AI safety flag indicating if command is safe
        
        Returns:
            ExecutionResult with execution details
        """
        # Construct the full command
        full_command = command
        if args:
            full_command = f"{command} {args}"
        
        # Evaluate command safety with TrustManager
        trust_result = self._evaluate_command_trust(full_command, is_safe)
        if trust_result is not None:
            return trust_result
        
        # Handle cd commands specially
        if command.strip() == 'cd' or command.strip().startswith('cd '):
            return self._handle_cd_command(full_command)
        
        # Track directory before execution
        old_directory = self._current_directory
        
        try:
            # Execute the command based on shell type
            if self._shell_type == 'powershell':
                result = subprocess.run(
                    ['powershell.exe', '-Command', full_command],
                    cwd=self._current_directory,
                    capture_output=True,
                    timeout=30,
                    encoding='utf-8',
                    errors='replace'
                )
            else:
                result = subprocess.run(
                    full_command,
                    shell=True,
                    cwd=self._current_directory,
                    capture_output=True,
                    timeout=30,
                    encoding='utf-8',
                    errors='replace'
                )
            
            # Get output and error
            output = result.stdout
            error = result.stderr
            
            # Strip trailing whitespace from each line (removes PowerShell padding)
            # This preserves structure but removes unnecessary spaces that inflate char counts
            output = strip_line_padding(output)
            
            # Cache the output if bash_tool is available
            cache_id = None
            if self._bash_tool and output:
                # Store in cache
                cache_id = self._bash_tool._output_cache.store(full_command, output)
            
            # Check if directory changed
            new_directory = self._current_directory
            directory_changed = (old_directory != new_directory)
            
            # Determine success
            if result.returncode == 0:
                return ExecutionResult(
                    success=True,
                    output=output if output else "Command completed successfully",
                    error=None,
                    directory_changed=directory_changed,
                    new_directory=new_directory if directory_changed else None,
                    cache_id=cache_id
                )
            else:
                return ExecutionResult(
                    success=False,
                    output=output if output else "",
                    error=error if error else f"Command failed with exit code {result.returncode}",
                    directory_changed=directory_changed,
                    new_directory=new_directory if directory_changed else None,
                    cache_id=cache_id
                )
        
        except subprocess.TimeoutExpired:
            return ExecutionResult(
                success=False,
                output="",
                error="Command timed out after 30 seconds"
            )
        
        except Exception as e:
            return ExecutionResult(
                success=False,
                output="",
                error=f"Error executing command: {str(e)}"
            )
    
    def _handle_cd_command(self, command: str) -> ExecutionResult:
        """Handle cd command to change working directory.
        
        Args:
            command: The cd command to execute
        
        Returns:
            ExecutionResult indicating success or failure of directory change
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
            return ExecutionResult(
                success=False,
                output="",
                error=f"cd: {target_dir}: No such file or directory"
            )
        
        if not os.path.isdir(target_dir):
            return ExecutionResult(
                success=False,
                output="",
                error=f"cd: {target_dir}: Not a directory"
            )
        
        # Check if directory actually changed
        old_directory = self._current_directory
        self._current_directory = target_dir
        directory_changed = (old_directory != target_dir)
        
        return ExecutionResult(
            success=True,
            output=f"Changed directory to {target_dir}",
            error=None,
            directory_changed=directory_changed,
            new_directory=target_dir if directory_changed else None
        )
    
    def get_current_directory(self) -> str:
        """Get the current working directory.
        
        Returns:
            The current working directory path
        """
        return self._current_directory
    
    def set_bash_tool(self, bash_tool) -> None:
        """Set the bash tool for caching support.
        
        Args:
            bash_tool: BashTool instance to use for caching
        """
        self._bash_tool = bash_tool
