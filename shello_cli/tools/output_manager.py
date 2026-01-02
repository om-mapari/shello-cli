"""Output management for handling large command outputs."""

from dataclasses import dataclass, field
from typing import Optional, Dict, Generator
from enum import Enum


class OutputType(Enum):
    """Types of command output with different truncation limits."""
    LIST = "list"           # ls, dir, docker ps - 50 lines
    SEARCH = "search"       # grep, find - 100 lines
    LOG = "log"             # tail, cat logs - 200 lines
    JSON = "json"           # JSON output - 500 lines
    DEFAULT = "default"     # Unknown type - 100 lines


@dataclass
class TruncationResult:
    """Result of output truncation.
    
    Attributes:
        output: The (possibly truncated) output string
        was_truncated: Whether truncation occurred
        total_lines: Total number of lines in original output
        shown_lines: Number of lines shown after truncation
        output_type: Detected type of the output
        warning: Optional truncation warning message
    """
    output: str
    was_truncated: bool
    total_lines: int
    shown_lines: int
    output_type: OutputType
    warning: Optional[str] = None


@dataclass
class OutputManagementConfig:
    """Output management configuration.
    
    Attributes:
        enabled: Whether output management is enabled
        show_warnings: Whether to show truncation warnings
        limits: Custom truncation limits per output type
        safety_limit: Maximum lines even with override (default: 1000)
    """
    enabled: bool = True
    show_warnings: bool = True
    limits: Dict[str, int] = field(default_factory=lambda: {
        "list": 50,
        "search": 100,
        "log": 200,
        "json": 500,
        "default": 100
    })
    safety_limit: int = 1000


# Default limits used as fallback when no configuration exists
DEFAULT_LIMITS = {
    "list": 50,
    "search": 100,
    "log": 200,
    "json": 500,
    "default": 100
}



import re


class Truncator:
    """Handles output truncation with type-specific logic."""
    
    def __init__(self, json_analyzer: Optional['JsonAnalyzerTool'] = None):
        """Initialize with optional JSON analyzer for automatic analysis.
        
        Args:
            json_analyzer: Optional JsonAnalyzerTool instance for JSON analysis
        """
        self._json_analyzer = json_analyzer
    
    def truncate(
        self, 
        output: str, 
        limit: int,
        output_type: OutputType
    ) -> TruncationResult:
        """Truncate output to the specified limit.
        
        Args:
            output: The output string to truncate
            limit: Maximum number of lines to show
            output_type: Type of output being truncated
            
        Returns:
            TruncationResult with truncation metadata
        """
        # Handle JSON specially
        if output_type == OutputType.JSON:
            return self.truncate_json(output, limit)
        
        # Basic line-based truncation
        lines = output.split('\n')
        total_lines = len(lines)
        
        # No truncation needed
        if total_lines <= limit:
            return TruncationResult(
                output=output,
                was_truncated=False,
                total_lines=total_lines,
                shown_lines=total_lines,
                output_type=output_type,
                warning=None
            )
        
        # Truncate to limit
        truncated_lines = lines[:limit]
        truncated_output = '\n'.join(truncated_lines)
        
        # Format warning
        warning = self.format_warning(total_lines, limit, output_type)
        
        return TruncationResult(
            output=truncated_output,
            was_truncated=True,
            total_lines=total_lines,
            shown_lines=limit,
            output_type=output_type,
            warning=warning
        )
    
    def truncate_json(self, output: str, limit: int) -> TruncationResult:
        """Truncate JSON output while preserving valid syntax.
        
        When JSON is truncated, automatically runs analyze_json tool
        and includes the structure summary in the result.
        
        Args:
            output: JSON output string
            limit: Maximum number of lines
            
        Returns:
            TruncationResult with JSON-specific handling
        """
        import json
        
        lines = output.split('\n')
        total_lines = len(lines)
        
        # No truncation needed
        if total_lines <= limit:
            return TruncationResult(
                output=output,
                was_truncated=False,
                total_lines=total_lines,
                shown_lines=total_lines,
                output_type=OutputType.JSON,
                warning=None
            )
        
        # Try to parse and truncate at object boundaries
        try:
            data = json.loads(output)
            json_structure = None
            
            # Run analyze_json if available
            if self._json_analyzer:
                analysis_result = self._json_analyzer.analyze(output)
                if analysis_result.success:
                    json_structure = analysis_result.output
            
            # If it's an array, truncate at object boundaries
            if isinstance(data, list):
                # Calculate how many items we can fit in the limit
                truncated_items = []
                current_lines = 2  # Account for opening [ and closing ]
                
                for item in data:
                    item_json = json.dumps(item, indent=2)
                    item_lines = len(item_json.split('\n'))
                    
                    if current_lines + item_lines + 1 <= limit:  # +1 for comma
                        truncated_items.append(item)
                        current_lines += item_lines + 1
                    else:
                        break
                
                # Create valid JSON with truncated items
                truncated_output = json.dumps(truncated_items, indent=2)
                shown_lines = len(truncated_output.split('\n'))
                
                warning = self.format_warning(
                    total_lines, 
                    shown_lines, 
                    OutputType.JSON,
                    json_structure
                )
                
                return TruncationResult(
                    output=truncated_output,
                    was_truncated=True,
                    total_lines=total_lines,
                    shown_lines=shown_lines,
                    output_type=OutputType.JSON,
                    warning=warning
                )
            
            # For objects or other JSON, fall back to line-based truncation
            # but try to keep it valid
            truncated_lines = lines[:limit]
            truncated_output = '\n'.join(truncated_lines)
            
            warning = self.format_warning(
                total_lines,
                limit,
                OutputType.JSON,
                json_structure
            )
            
            return TruncationResult(
                output=truncated_output,
                was_truncated=True,
                total_lines=total_lines,
                shown_lines=limit,
                output_type=OutputType.JSON,
                warning=warning
            )
            
        except (json.JSONDecodeError, Exception):
            # Fall back to line-based truncation if JSON parsing fails
            truncated_lines = lines[:limit]
            truncated_output = '\n'.join(truncated_lines)
            
            warning = self.format_warning(total_lines, limit, OutputType.JSON)
            
            return TruncationResult(
                output=truncated_output,
                was_truncated=True,
                total_lines=total_lines,
                shown_lines=limit,
                output_type=OutputType.JSON,
                warning=warning
            )
    
    def format_warning(
        self,
        total_lines: int,
        shown_lines: int,
        output_type: OutputType,
        json_structure: Optional[str] = None
    ) -> str:
        """Format the truncation warning message.
        
        For JSON, includes the structure analysis from analyze_json tool.
        
        Args:
            total_lines: Total number of lines in original output
            shown_lines: Number of lines shown
            output_type: Type of output
            json_structure: Optional JSON structure analysis
            
        Returns:
            Formatted warning message
        """
        percentage = int((shown_lines / total_lines) * 100)
        
        warning = f"\n\n⚠️  Output truncated ({total_lines} lines total, showing first {shown_lines} - {percentage}%)"
        
        # Add JSON structure if available
        if json_structure and output_type == OutputType.JSON:
            warning += f"\n\n📊 JSON Structure:\n{json_structure}"
            warning += "\n\n💡 Use jq to filter the output"
        
        return warning


class OutputManager:
    """Manages command output truncation and type detection.
    
    This component sits between tool execution and result processing,
    applying intelligent truncation based on output type.
    All limits are configurable through ~/.shello_cli/user-settings.json via SettingsManager.
    """
    
    def __init__(self, config: Optional[OutputManagementConfig] = None):
        """Initialize with optional configuration.
        
        If no config provided, loads from SettingsManager.
        Falls back to defaults if settings not found.
        
        Args:
            config: Optional OutputManagementConfig. If None, loads from SettingsManager.
        """
        if config is None:
            # Load from SettingsManager
            from shello_cli.utils.settings_manager import SettingsManager
            config = SettingsManager.get_instance().get_output_management_config()
        
        self._config = config
        self._type_detector = TypeDetector()
        self._truncator = Truncator()
    
    @classmethod
    def from_settings(cls) -> 'OutputManager':
        """Create OutputManager from current project settings.
        
        Returns:
            OutputManager instance with settings from SettingsManager
        """
        return cls(config=None)
    
    def process_output(
        self, 
        output: str, 
        command: str,
        override_limit: bool = False
    ) -> TruncationResult:
        """Process command output and apply truncation if needed.
        
        Args:
            output: The command output to process
            command: The command that generated the output
            override_limit: If True, use safety limit instead of type-specific limit
            
        Returns:
            TruncationResult with truncation metadata
        """
        # Check if output management is enabled
        if not self._config.enabled:
            # Return output as-is without truncation
            lines = output.split('\n')
            return TruncationResult(
                output=output,
                was_truncated=False,
                total_lines=len(lines),
                shown_lines=len(lines),
                output_type=OutputType.DEFAULT,
                warning=None
            )
        
        # Detect output type
        output_type = self._type_detector.detect(command, output)
        
        # Get appropriate limit
        if override_limit:
            limit = self._config.safety_limit
        else:
            limit = self.get_limit_for_type(output_type)
        
        # Apply truncation
        result = self._truncator.truncate(output, limit, output_type)
        
        # Add file export suggestion if safety limit was reached with override
        if override_limit and result.was_truncated and result.shown_lines >= self._config.safety_limit:
            if result.warning:
                result.warning += "\n\n💾 Consider exporting to a file instead: command > output.txt"
        
        return result
    
    def detect_output_type(self, command: str, output: str) -> OutputType:
        """Detect the type of output based on command and content.
        
        Args:
            command: The command string
            output: The output string
            
        Returns:
            Detected OutputType
        """
        return self._type_detector.detect(command, output)
    
    def get_limit_for_type(self, output_type: OutputType) -> int:
        """Get the truncation limit for a given output type from config.
        
        Args:
            output_type: The type of output
            
        Returns:
            Line limit for the given type
        """
        return self._config.limits.get(output_type.value, DEFAULT_LIMITS[output_type.value])
    
    def is_enabled(self) -> bool:
        """Check if output management is enabled in config.
        
        Returns:
            True if enabled, False otherwise
        """
        return self._config.enabled
    
    def process_stream(
        self,
        stream: Generator[str, None, None],
        command: str,
        override_limit: bool = False
    ) -> Generator[str, None, TruncationResult]:
        """Process streaming output with real-time truncation.
        
        Yields output immediately as it arrives, counts lines in real-time,
        and stops yielding after reaching the limit.
        
        Args:
            stream: Generator yielding output chunks
            command: The command that generated the output
            override_limit: If True, use safety limit instead of type-specific limit
            
        Yields:
            Output chunks until limit is reached
            
        Returns:
            TruncationResult with truncation metadata
        """
        # Check if output management is enabled
        if not self._config.enabled:
            # Pass through all chunks without truncation
            accumulated_output = []
            for chunk in stream:
                accumulated_output.append(chunk)
                yield chunk
            
            full_output = ''.join(accumulated_output)
            lines = full_output.split('\n')
            if full_output.endswith('\n'):
                total_lines = len(lines) - 1
            else:
                total_lines = len(lines)
            
            return TruncationResult(
                output=full_output,
                was_truncated=False,
                total_lines=total_lines,
                shown_lines=total_lines,
                output_type=OutputType.DEFAULT,
                warning=None
            )
        
        # For real-time streaming, detect type from command only initially
        # We'll refine detection after first chunk if needed
        output_type = self._type_detector.detect(command, "")
        
        # Get appropriate limit
        if override_limit:
            limit = self._config.safety_limit
        else:
            limit = self.get_limit_for_type(output_type)
        
        accumulated_output = ""
        current_line_count = 0
        truncated = False
        type_detected = False
        
        for chunk in stream:
            accumulated_output += chunk
            
            # Re-detect type after first chunk with actual content (for JSON detection)
            if not type_detected and len(accumulated_output) > 10:
                output_type = self._type_detector.detect(command, accumulated_output)
                if not override_limit:
                    limit = self.get_limit_for_type(output_type)
                type_detected = True
            
            # Count lines
            current_line_count = accumulated_output.count('\n')
            
            # Check if we've EXCEEDED the limit (not just reached it)
            if current_line_count > limit:
                truncated = True
                # Consume remaining chunks to get total count, but don't yield
                for remaining_chunk in stream:
                    accumulated_output += remaining_chunk
                break
            
            # Yield immediately for real-time output
            yield chunk
        
        # Calculate final statistics
        total_lines = accumulated_output.count('\n')
        if accumulated_output and not accumulated_output.endswith('\n'):
            total_lines += 1  # Count last line without newline
        
        # Only truncated if we stopped early (total > limit)
        was_truncated = total_lines > limit
        
        if was_truncated:
            lines = accumulated_output.split('\n')
            truncated_lines = lines[:limit]
            truncated_output = '\n'.join(truncated_lines)
            if limit > 0:
                truncated_output += '\n'
            shown_lines = limit
            percentage = int((shown_lines / total_lines) * 100)
            warning = f"\n\n⚠️  Output truncated ({total_lines} lines total, showing first {shown_lines} - {percentage}%)"
            
            # Add file export suggestion if safety limit was reached with override
            if override_limit and shown_lines >= self._config.safety_limit:
                warning += "\n\n💾 Consider exporting to a file instead: command > output.txt"
            
            # Yield the truncation warning as final chunk
            yield warning
            
            return TruncationResult(
                output=truncated_output,
                was_truncated=True,
                total_lines=total_lines,
                shown_lines=shown_lines,
                output_type=output_type,
                warning=warning
            )
        else:
            # No truncation needed
            return TruncationResult(
                output=accumulated_output,
                was_truncated=False,
                total_lines=total_lines,
                shown_lines=total_lines,
                output_type=output_type,
                warning=None
            )


class TypeDetector:
    """Detects output type from command and content analysis.
    
    Works across all shells (PowerShell, bash, cmd) using regex patterns.
    JSON detection is a simple content check - deep analysis is delegated
    to the existing analyze_json tool.
    """
    
    # Command keywords for type detection (cross-shell compatible)
    LIST_KEYWORDS = [
        r'\bls\b', r'\bdir\b', r'docker\s+ps', r'kubectl\s+get',
        r'Get-ChildItem', r'aws\s+\w+\s+list'
    ]
    SEARCH_KEYWORDS = [
        r'\bgrep\b', r'\bfind\b', r'\bsearch\b',
        r'Select-String', r'\bfindstr\b'
    ]
    LOG_KEYWORDS = [
        r'\btail\b', r'cat\s+.*\.log', r'\bjournalctl\b',
        r'Get-Content\s+.*\.log'
    ]
    
    def detect_from_command(self, command: str) -> Optional[OutputType]:
        """Detect output type from command keywords using regex.
        
        Args:
            command: The command string to analyze
            
        Returns:
            OutputType if detected, None otherwise
        """
        # Check for list commands
        for pattern in self.LIST_KEYWORDS:
            if re.search(pattern, command, re.IGNORECASE):
                return OutputType.LIST
        
        # Check for search commands
        for pattern in self.SEARCH_KEYWORDS:
            if re.search(pattern, command, re.IGNORECASE):
                return OutputType.SEARCH
        
        # Check for log commands
        for pattern in self.LOG_KEYWORDS:
            if re.search(pattern, command, re.IGNORECASE):
                return OutputType.LOG
        
        return None
    
    def detect_from_content(self, output: str) -> Optional[OutputType]:
        """Quick check if output looks like JSON.
        
        Simple check - just looks for { or [ at start.
        Deep JSON analysis is delegated to the existing analyze_json tool.
        
        Args:
            output: The output string to analyze
            
        Returns:
            OutputType.JSON if detected, None otherwise
        """
        stripped = output.strip()
        if stripped.startswith('{') or stripped.startswith('['):
            return OutputType.JSON
        return None
    
    def detect(self, command: str, output: str) -> OutputType:
        """Detect output type using both command and content analysis.
        
        Priority:
        1. Content-based detection (JSON takes precedence)
        2. Command-based detection
        3. DEFAULT if nothing matches
        
        Args:
            command: The command string
            output: The output string
            
        Returns:
            Detected OutputType
        """
        # Content-based detection takes precedence (especially for JSON)
        content_type = self.detect_from_content(output)
        if content_type is not None:
            return content_type
        
        # Fall back to command-based detection
        command_type = self.detect_from_command(command)
        if command_type is not None:
            return command_type
        
        # Default if nothing matches
        return OutputType.DEFAULT
