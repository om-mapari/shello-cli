"""
Data models for the Shello Agent.

This module contains dataclasses used throughout the agent system.
"""

from dataclasses import dataclass
from typing import List, Optional, Any
from datetime import datetime


@dataclass
class ChatEntry:
    """Represents an entry in chat history.
    
    Attributes:
        type: Type of entry ("user", "assistant", "tool_result", "tool_call")
        content: The content of the entry
        timestamp: When the entry was created
        tool_calls: Optional list of tool calls from assistant
        tool_call: Optional single tool call information
        tool_result: Optional tool execution result
    """
    type: str
    content: str
    timestamp: datetime
    tool_calls: Optional[List[Any]] = None
    tool_call: Optional[Any] = None
    tool_result: Optional[Any] = None


@dataclass
class StreamingChunk:
    """Chunk from streaming response.
    
    Attributes:
        type: Type of chunk ("content", "tool_calls", "tool_result", "tool_output", "done")
        content: Optional content string
        tool_calls: Optional list of tool calls
        tool_call: Optional single tool call
        tool_result: Optional tool result
    """
    type: str
    content: Optional[str] = None
    tool_calls: Optional[List[Any]] = None
    tool_call: Optional[Any] = None
    tool_result: Optional[Any] = None
