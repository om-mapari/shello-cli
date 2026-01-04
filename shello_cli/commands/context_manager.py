"""Context manager for tracking direct command execution history and AI synchronization."""

from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime


@dataclass
class CommandRecord:
    """Record of a direct command execution."""
    command: str
    output: str
    success: bool
    timestamp: datetime
    directory: str
    cache_id: Optional[str] = None  # Cache ID for retrieving full output
    sent_to_ai: bool = False  # Track if this command was already sent to AI


class ContextManager:
    """Manages command history and AI context synchronization."""
    
    def __init__(self):
        self._command_history: List[CommandRecord] = []
        self._current_directory: str = ""
    
    def record_command(self, command: str, output: str, success: bool, directory: str, cache_id: Optional[str] = None) -> None:
        """Record a direct command execution for AI context.
        
        Args:
            command: The command that was executed
            output: The output from the command (will be truncated if too long)
            success: Whether the command succeeded
            directory: The working directory where command was executed
            cache_id: Optional cache ID for retrieving full output
        """
        # Truncate output if too long (keep first 500 chars)
        truncated_output = output[:500] if len(output) > 500 else output
        
        record = CommandRecord(
            command=command,
            output=truncated_output,
            success=success,
            timestamp=datetime.now(),
            directory=directory,
            cache_id=cache_id
        )
        
        self._command_history.append(record)
        self._current_directory = directory
        
        # Keep only last 10 commands to prevent history from growing too large
        if len(self._command_history) > 10:
            self._command_history = self._command_history[-10:]
    
    def get_context_for_ai(self) -> str:
        """Generate context string for AI about recent direct commands.
        
        Only includes commands that haven't been sent to AI yet.
        Marks commands as sent after generating context.
        
        Returns:
            A formatted string containing NEW command history for AI context
        """
        # Get only commands that haven't been sent to AI yet
        new_commands = [cmd for cmd in self._command_history if not cmd.sent_to_ai]
        
        if not new_commands:
            return ""
        
        context_lines = ["Recent direct commands executed:"]
        
        for record in new_commands:
            status = "✓" if record.success else "✗"
            cmd_line = f"{status} [{record.directory}] $ {record.command}"
            if record.cache_id:
                cmd_line += f" (cache_id: {record.cache_id})"
            context_lines.append(cmd_line)
            # Mark as sent to AI
            record.sent_to_ai = True
        
        return "\n".join(context_lines)
    
    def clear_history(self) -> None:
        """Clear command history (e.g., on /new command)."""
        self._command_history.clear()
        self._current_directory = ""
