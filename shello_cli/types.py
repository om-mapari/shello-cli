"""
Type definitions for Shello CLI.

This module contains centralized type definitions used throughout the application,
including tool-related dataclasses for OpenAI function calling integration.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from shello_cli.tools.output_manager import TruncationResult


@dataclass
class ToolResult:
    """Standardized result from tool execution.
    
    Attributes:
        success: Whether the tool execution was successful
        output: Output string on success
        error: Error message on failure
        data: Optional additional data from the tool
        truncation_info: Optional truncation metadata
        api_content: The exact JSON string sent to the AI as the tool result message
                     content (includes truncation metadata and cache IDs). Set by
                     MessageProcessor after building the tool_result_content dict.
                     Used by SessionRecorder to store what the AI actually saw.
    """
    success: bool
    output: Optional[str] = None
    error: Optional[str] = None
    data: Optional[Any] = None
    truncation_info: Optional['TruncationResult'] = None
    api_content: Optional[str] = None


@dataclass
class ShelloTool:
    """Tool definition for OpenAI function calling.
    
    Attributes:
        type: The type of tool, always "function" for function calling
        function: Dictionary containing name, description, and parameters schema
    """
    type: str
    function: Dict[str, Any]


@dataclass
class ShelloToolCall:
    """Tool call from AI response.
    
    Attributes:
        id: Unique identifier for the tool call
        type: The type of tool call, always "function"
        function: Dictionary with name and arguments (JSON string)
    """
    id: str
    type: str
    function: Dict[str, str]
