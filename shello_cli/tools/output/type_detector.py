"""Output type detection based on command and content patterns."""

import re
from typing import Optional

from shello_cli.patterns import COMMAND_PATTERNS, CONTENT_PATTERNS
from shello_cli.tools.output.types import OutputType


class TypeDetector:
    """Detects output type from command and content.
    
    Content-based detection takes precedence over command-based detection.
    This allows accurate classification even when commands produce unexpected output.
    """
    
    def __init__(self):
        """Initialize the type detector with compiled regex patterns."""
        # Compile command patterns for efficiency
        self._command_patterns = {}
        for output_type, patterns in COMMAND_PATTERNS.items():
            self._command_patterns[output_type] = [
                re.compile(pattern, re.IGNORECASE) for pattern in patterns
            ]
        
        # Compile content patterns for efficiency
        self._content_patterns = {}
        for output_type, patterns in CONTENT_PATTERNS.items():
            self._content_patterns[output_type] = [
                re.compile(pattern, re.IGNORECASE | re.MULTILINE) for pattern in patterns
            ]
    
    def detect_from_command(self, command: str) -> Optional[OutputType]:
        """Detect output type from command string.
        
        Args:
            command: The command string to analyze
            
        Returns:
            OutputType if detected, None otherwise
        """
        if not command:
            return None
        
        # Check each output type's patterns
        for output_type_str, patterns in self._command_patterns.items():
            for pattern in patterns:
                if pattern.search(command):
                    return OutputType(output_type_str)
        
        return None
    
    def detect_from_content(self, output: str) -> Optional[OutputType]:
        """Detect output type from content.
        
        Args:
            output: The output content to analyze
            
        Returns:
            OutputType if detected, None otherwise
        """
        if not output:
            return None
        
        # Check each output type's content patterns
        for output_type_str, patterns in self._content_patterns.items():
            for pattern in patterns:
                if pattern.search(output):
                    return OutputType(output_type_str)
        
        return None
    
    def detect(self, command: str, output: str) -> OutputType:
        """Detect output type from both command and content.
        
        Content detection takes precedence over command detection.
        Falls back to DEFAULT if no type is detected.
        
        Args:
            command: The command string
            output: The output content
            
        Returns:
            Detected OutputType (never None, defaults to DEFAULT)
        """
        # Try content-based detection first (takes precedence)
        content_type = self.detect_from_content(output)
        if content_type is not None:
            return content_type
        
        # Fall back to command-based detection
        command_type = self.detect_from_command(command)
        if command_type is not None:
            return command_type
        
        # Default if nothing detected
        return OutputType.DEFAULT
