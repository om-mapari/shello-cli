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
            # Apply heuristics to detect natural language vs shell commands
            if self._looks_like_natural_language(user_input, first_word, args):
                return DetectionResult(
                    input_type=InputType.AI_QUERY,
                    original_input=user_input
                )
            
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
    
    def _looks_like_natural_language(self, full_input: str, command: str, args: Optional[str]) -> bool:
        """Heuristics to detect if input is natural language rather than a shell command.
        
        Args:
            full_input: The complete user input
            command: The first word (potential command)
            args: The rest of the input after the first word
            
        Returns:
            True if input appears to be natural language, False if it looks like a shell command
        """
        if not args:
            # Single word commands are likely shell commands
            return False
        
        args_lower = args.lower()
        
        # Strong natural language indicators - phrases that are very unlikely in shell commands
        strong_indicators = [
            'are you', 'do you', 'can you', 'will you', 'would you', 'could you',
            'should i', 'how do', 'what is', 'what are', 'why is', 'when is',
            'where is', 'who is', 'tell me', 'show me', 'explain', 'describe',
            'please', 'i want', 'i need', 'help me'
        ]
        
        # Check if args contain strong natural language patterns
        for indicator in strong_indicators:
            if indicator in args_lower:
                return True
        
        # Check for question marks at the end with natural language context
        # Only if there are clear question words before it
        if full_input.rstrip().endswith('?'):
            question_words = ['what', 'which', 'where', 'when', 'why', 'who', 'how']
            # Check if any question word appears in the input (not just as the command)
            input_words = full_input.lower().split()
            if len(input_words) > 1 and any(word in input_words[1:] for word in question_words):
                return True
        
        # Special handling for "which" command - it's often used in questions
        if command == 'which':
            # If args contain words that suggest a question rather than a path/command
            question_context = ['model', 'version', 'one', 'option', 'way', 'better', 'best']
            if any(word in args_lower for word in question_context):
                return True
            # If args have multiple words (more than 2), likely natural language
            if len(args.split()) > 2:
                return True
        
        # Special handling for "find" command - can be used in natural language
        if command == 'find':
            # If it starts with "find out", "find me", etc., it's natural language
            if args_lower.startswith(('out', 'me', 'the way', 'how')):
                return True
        
        return False
