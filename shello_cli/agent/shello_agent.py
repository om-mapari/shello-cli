"""
Shello Agent for orchestrating AI conversations and tool execution.

This module provides the ShelloAgent class that manages conversation history,
processes user messages, executes tools, and handles streaming responses.
"""

import json
import platform
from typing import List, Optional, Generator, Any, Dict
from datetime import datetime

from shello_cli.api.openai_client import ShelloClient
from shello_cli.tools.tools import get_tool_descriptions
from shello_cli.agent.template import INSTRUCTION_TEMPLATE
from shello_cli.agent.models import ChatEntry, StreamingChunk
from shello_cli.agent.tool_executor import ToolExecutor
from shello_cli.agent.message_processor import MessageProcessor
from shello_cli.utils.system_info import (
    detect_shell,
    load_custom_instructions,
    get_current_datetime
)


class ShelloAgent:
    """AI agent that processes messages and executes tools.
    
    The agent maintains conversation history, sends messages to the OpenAI API,
    executes tools when requested by the AI, and manages the tool execution loop.
    
    Attributes:
        _client: The OpenAI client for API communication
        _tool_executor: The tool executor for running tools
        _message_processor: The message processor for handling conversation flow
        _chat_history: List of chat entries
        _messages: List of messages in OpenAI format
    """
    
    def __init__(
        self,
        api_key: str,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        max_tool_rounds: int = 100
    ):
        """Initialize agent with API credentials.
        
        Args:
            api_key: OpenAI API key for authentication
            base_url: Optional custom base URL for OpenAI-compatible endpoints
            model: Optional model name (defaults to "gpt-4o")
            max_tool_rounds: Maximum number of tool execution rounds (default: 100)
        """
        # Initialize the OpenAI client
        self._client = ShelloClient(
            api_key=api_key,
            model=model or "gpt-4o",
            base_url=base_url
        )
        
        # Initialize components
        self._tool_executor = ToolExecutor()
        self._message_processor = MessageProcessor(
            client=self._client,
            tool_executor=self._tool_executor,
            max_tool_rounds=max_tool_rounds
        )
        
        # Initialize conversation tracking
        self._chat_history: List[ChatEntry] = []
        self._messages: List[Dict[str, Any]] = []
        
        # Build and add system message
        system_prompt = self._build_system_prompt()
        self._messages.append({
            "role": "system",
            "content": system_prompt
        })
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt with current system information.
        
        Returns:
            The formatted system prompt
        """
        # Load custom instructions if available
        custom_instructions = load_custom_instructions()
        custom_instructions_section = ""
        if custom_instructions:
            custom_instructions_section = (
                f"\n\nCUSTOM INSTRUCTIONS:\n{custom_instructions}\n\n"
                "The above custom instructions should be followed alongside the standard instructions below."
            )
        
        # Get system information
        os_name = platform.system()
        shell_name, shell_executable = detect_shell()
        cwd = self._tool_executor.get_current_directory()
        current_datetime = get_current_datetime()
        
        # Get tool descriptions dynamically
        tool_descriptions = get_tool_descriptions()
        
        # Format the system prompt with current information
        return INSTRUCTION_TEMPLATE.format(
            custom_instructions=custom_instructions_section,
            tool_descriptions=tool_descriptions,
            os_name=os_name,
            shell=shell_name,
            shell_executable=shell_executable,
            cwd=cwd,
            current_datetime=current_datetime
        )
    
    def process_user_message(self, message: str) -> List[ChatEntry]:
        """Process a user message and return chat entries.
        
        This method sends the user message to the AI, executes any requested tools,
        and continues the conversation loop until the AI provides a final response.
        
        Args:
            message: The user's message
        
        Returns:
            List of ChatEntry objects representing the conversation flow
        """
        # Add user message to history
        user_entry = ChatEntry(
            type="user",
            content=message,
            timestamp=datetime.now()
        )
        self._chat_history.append(user_entry)
        
        # Add user message to messages
        self._messages.append({
            "role": "user",
            "content": message
        })
        
        # Process through message processor
        entries = self._message_processor.process_message(
            messages=self._messages,
            chat_history=self._chat_history
        )
        
        return entries
    
    def process_user_message_stream(self, message: str) -> Generator[StreamingChunk, None, None]:
        """Process a user message with streaming response.
        
        This method sends the user message to the AI and yields streaming chunks
        as they arrive, including tool execution results.
        
        Args:
            message: The user's message
        
        Yields:
            StreamingChunk objects representing the conversation flow
        """
        # Add user message to history
        user_entry = ChatEntry(
            type="user",
            content=message,
            timestamp=datetime.now()
        )
        self._chat_history.append(user_entry)
        
        # Add user message to messages
        self._messages.append({
            "role": "user",
            "content": message
        })
        
        # Process through message processor with streaming
        yield from self._message_processor.process_message_stream(
            messages=self._messages,
            chat_history=self._chat_history
        )
    
    def get_chat_history(self) -> List[ChatEntry]:
        """Get the full chat history.
        
        Returns:
            List of all ChatEntry objects in chronological order
        """
        return self._chat_history.copy()
    
    def add_system_message(self, message: str) -> None:
        """Add a system message to the conversation context.
        
        Used for notifying the AI about events like user interrupts.
        
        Args:
            message: The system message to add
        """
        self._messages.append({
            "role": "system",
            "content": message
        })
        # Also add to chat history for tracking
        self._chat_history.append(ChatEntry(
            type="system",
            content=message,
            timestamp=datetime.now()
        ))
    
    def add_interrupted_tool_response(self, tool_call_id: str, command: str) -> None:
        """Add a tool response for an interrupted tool call.
        
        This ensures the message history stays valid (matching tool calls with responses).
        
        Args:
            tool_call_id: The ID of the interrupted tool call
            command: The command that was interrupted
        """
        self._messages.append({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": json.dumps({
                "success": False,
                "output": None,
                "error": f"Execution interrupted by user (Ctrl+C). Command: {command}"
            })
        })
        # Add to chat history
        self._chat_history.append(ChatEntry(
            type="tool_result",
            content=f"[Interrupted by user] {command}",
            timestamp=datetime.now()
        ))
    
    def get_pending_tool_calls(self) -> list:
        """Get any pending tool calls that don't have responses.
        
        Returns:
            List of tool call IDs that need responses
        """
        # Find assistant messages with tool_calls
        tool_call_ids = set()
        tool_response_ids = set()
        
        for msg in self._messages:
            if msg.get("role") == "assistant" and msg.get("tool_calls"):
                for tc in msg["tool_calls"]:
                    tool_call_ids.add(tc.get("id"))
            elif msg.get("role") == "tool":
                tool_response_ids.add(msg.get("tool_call_id"))
        
        # Return IDs that have calls but no responses
        pending = tool_call_ids - tool_response_ids
        return list(pending)
    
    def get_current_directory(self) -> str:
        """Get the current working directory.
        
        Returns:
            The current working directory path
        """
        return self._tool_executor.get_current_directory()
    
    def get_current_model(self) -> str:
        """Get the current model.
        
        Returns:
            The name of the current model
        """
        return self._client.get_current_model()
    
    def set_model(self, model: str) -> None:
        """Set the current model.
        
        Args:
            model: The model name to use
        """
        self._client.set_model(model)
    
    def clear_cache(self) -> None:
        """Clear the output cache.
        
        This should be called when starting a new conversation or ending the session.
        """
        self._tool_executor.clear_cache()
    
    def get_bash_tool(self):
        """Get the bash tool instance for direct command caching.
        
        Returns:
            The BashTool instance used by the agent
        """
        return self._tool_executor._bash_tool
