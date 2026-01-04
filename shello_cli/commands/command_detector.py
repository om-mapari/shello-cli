"""Command detection for direct execution vs AI routing"""
from dataclasses import dataclass
from typing import Optional, Set
from enum import Enum


class InputType(Enum):
    """Classification of user input types"""
    DIRECT_COMMAND = "direct_command"
    AI_QUERY = "ai_query"
    INTERNAL_COMMAND = "internal_command"


@dataclass
class DetectionResult:
    """Result of command detection analysis"""
    input_type: InputType
    command: Optional[str] = None
    args: Optional[str] = None
    original_input: str = ""


class CommandDetector:
    """Detects whether user input is a direct shell command or AI query."""
    
    # Commands that can be executed directly
    DIRECT_COMMANDS: Set[str] = {
        # Unix commands
        'ls', 'pwd', 'cd', 'cat', 'clear', 'echo', 'whoami', 'date',
        'mkdir', 'rmdir', 'touch', 'rm', 'cp', 'mv', 'head', 'tail',
        'wc', 'grep', 'find', 'which', 'env', 'export', 'tree',
        # Windows commands
        'dir', 'cls', 'type', 'copy', 'move', 'del', 'md', 'rd',
        'ren', 'where', 'set', 'hostname', 'ipconfig', 'systeminfo',
    }
    
    def detect(self, user_input: str) -> DetectionResult:
        """Analyze user input and determine how to process it.
        
        Simple logic: if input starts with a known command, it's direct.
        Otherwise, route to AI.
        
        Args:
            user_input: The raw user input string
            
        Returns:
            DetectionResult with classification and parsed components
        """
        # Handle empty or whitespace-only input
        if not user_input or not user_input.strip():
            return DetectionResult(
                input_type=InputType.AI_QUERY,
                original_input=user_input
            )
        
        # Split input into command and arguments
        parts = user_input.strip().split(maxsplit=1)
        first_word = parts[0].lower()
        args = parts[1] if len(parts) > 1 else None
        
        # Check if first word is a known direct command
        if first_word in self.DIRECT_COMMANDS:
            return DetectionResult(
                input_type=InputType.DIRECT_COMMAND,
                command=first_word,
                args=args,
                original_input=user_input
            )
        
        # Default to AI query for anything else
        return DetectionResult(
            input_type=InputType.AI_QUERY,
            original_input=user_input
        )
