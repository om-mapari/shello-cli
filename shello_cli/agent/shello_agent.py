"""
Shello Agent for orchestrating AI conversations and tool execution.

This module provides the ShelloAgent class that manages conversation history,
processes user messages, executes tools, and handles streaming responses.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Generator, Any, Dict
from datetime import datetime
import json
import os
import platform

from shello_cli.api.openai_client import ShelloClient
from shello_cli.tools.bash_tool import BashTool
from shello_cli.tools.tools import get_all_tools
from shello_cli.types import ToolResult
from shello_cli.agent.template import INSTRUCTION_TEMPLATE


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
        type: Type of chunk ("content", "tool_calls", "tool_result", "done")
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


class ShelloAgent:
    """AI agent that processes messages and executes tools.
    
    The agent maintains conversation history, sends messages to the OpenAI API,
    executes tools when requested by the AI, and manages the tool execution loop.
    
    Attributes:
        _client: The OpenAI client for API communication
        _bash_tool: The bash tool for command execution
        _chat_history: List of chat entries
        _messages: List of messages in OpenAI format
        _max_tool_rounds: Maximum number of tool execution rounds
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
        
        # Initialize the bash tool
        self._bash_tool = BashTool()
        
        # Initialize conversation tracking
        self._chat_history: List[ChatEntry] = []
        self._messages: List[Dict[str, Any]] = []
        
        # Store configuration
        self._max_tool_rounds = max_tool_rounds
        
        # Get system information
        os_name = platform.system()
        shell = os.environ.get('SHELL', 'cmd' if os_name == 'Windows' else 'bash')
        shell_executable = shell
        cwd = self._bash_tool.get_current_directory()
        current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Format the system prompt with current information
        system_prompt = INSTRUCTION_TEMPLATE.format(
            os_name=os_name,
            shell=os.path.basename(shell),
            shell_executable=shell_executable,
            cwd=cwd,
            current_datetime=current_datetime
        )
        
        # Add system message
        self._messages.append({
            "role": "system",
            "content": system_prompt
        })
    
    def process_user_message(self, message: str) -> List[ChatEntry]:
        """Process a user message and return chat entries.
        
        This method sends the user message to the AI, executes any requested tools,
        and continues the conversation loop until the AI provides a final response.
        
        Args:
            message: The user's message
        
        Returns:
            List of ChatEntry objects representing the conversation flow
        """
        entries: List[ChatEntry] = []
        
        # Add user message to history
        user_entry = ChatEntry(
            type="user",
            content=message,
            timestamp=datetime.now()
        )
        entries.append(user_entry)
        self._chat_history.append(user_entry)
        
        # Add user message to messages
        self._messages.append({
            "role": "user",
            "content": message
        })
        
        # Tool execution loop
        tool_rounds = 0
        while tool_rounds < self._max_tool_rounds:
            # Get response from AI
            try:
                response = self._client.chat(
                    messages=self._messages,
                    tools=get_all_tools()
                )
            except Exception as e:
                error_entry = ChatEntry(
                    type="assistant",
                    content=f"Error communicating with AI: {str(e)}",
                    timestamp=datetime.now()
                )
                entries.append(error_entry)
                self._chat_history.append(error_entry)
                return entries
            
            # Extract the assistant's message
            choice = response.get("choices", [{}])[0]
            message_data = choice.get("message", {})
            
            # Check if there are tool calls
            tool_calls = message_data.get("tool_calls")
            
            if tool_calls:
                # Add assistant message with tool calls to messages
                self._messages.append({
                    "role": "assistant",
                    "content": message_data.get("content"),
                    "tool_calls": tool_calls
                })
                
                # Create entry for tool calls
                tool_call_entry = ChatEntry(
                    type="tool_call",
                    content="",
                    timestamp=datetime.now(),
                    tool_calls=tool_calls
                )
                entries.append(tool_call_entry)
                self._chat_history.append(tool_call_entry)
                
                # Execute each tool call
                for tool_call in tool_calls:
                    tool_result = self._execute_tool(tool_call)
                    
                    # Add tool result to messages
                    self._messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.get("id"),
                        "content": json.dumps({
                            "success": tool_result.success,
                            "output": tool_result.output,
                            "error": tool_result.error
                        })
                    })
                    
                    # Create entry for tool result
                    result_entry = ChatEntry(
                        type="tool_result",
                        content=tool_result.output or tool_result.error or "",
                        timestamp=datetime.now(),
                        tool_call=tool_call,
                        tool_result=tool_result
                    )
                    entries.append(result_entry)
                    self._chat_history.append(result_entry)
                
                # Increment tool rounds counter
                tool_rounds += 1
            else:
                # No tool calls, this is the final response
                content = message_data.get("content", "")
                
                # Add assistant message to messages
                self._messages.append({
                    "role": "assistant",
                    "content": content
                })
                
                # Create entry for assistant response
                assistant_entry = ChatEntry(
                    type="assistant",
                    content=content,
                    timestamp=datetime.now()
                )
                entries.append(assistant_entry)
                self._chat_history.append(assistant_entry)
                
                # Exit the loop
                break
        
        # If we hit max tool rounds, add a warning
        if tool_rounds >= self._max_tool_rounds:
            warning_entry = ChatEntry(
                type="assistant",
                content=f"Maximum tool execution rounds ({self._max_tool_rounds}) reached.",
                timestamp=datetime.now()
            )
            entries.append(warning_entry)
            self._chat_history.append(warning_entry)
        
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
        
        # Tool execution loop
        tool_rounds = 0
        while tool_rounds < self._max_tool_rounds:
            # Get streaming response from AI
            try:
                stream = self._client.chat_stream(
                    messages=self._messages,
                    tools=get_all_tools()
                )
            except Exception as e:
                yield StreamingChunk(
                    type="content",
                    content=f"Error communicating with AI: {str(e)}"
                )
                return
            
            # Accumulate the response
            accumulated_content = ""
            accumulated_tool_calls: List[Dict[str, Any]] = []
            tool_call_accumulator: Dict[int, Dict[str, Any]] = {}
            
            for chunk in stream:
                choice = chunk.get("choices", [{}])[0]
                delta = choice.get("delta", {})
                
                # Handle content delta
                if "content" in delta and delta["content"]:
                    content_piece = delta["content"]
                    accumulated_content += content_piece
                    yield StreamingChunk(type="content", content=content_piece)
                
                # Handle tool calls delta
                if "tool_calls" in delta:
                    for tool_call_delta in delta["tool_calls"]:
                        index = tool_call_delta.get("index", 0)
                        
                        # Initialize tool call if not exists
                        if index not in tool_call_accumulator:
                            tool_call_accumulator[index] = {
                                "id": "",
                                "type": "function",
                                "function": {
                                    "name": "",
                                    "arguments": ""
                                }
                            }
                        
                        # Update tool call fields
                        if "id" in tool_call_delta:
                            tool_call_accumulator[index]["id"] = tool_call_delta["id"]
                        
                        if "function" in tool_call_delta:
                            func_delta = tool_call_delta["function"]
                            if "name" in func_delta:
                                tool_call_accumulator[index]["function"]["name"] = func_delta["name"]
                            if "arguments" in func_delta:
                                tool_call_accumulator[index]["function"]["arguments"] += func_delta["arguments"]
            
            # Convert accumulated tool calls to list
            if tool_call_accumulator:
                accumulated_tool_calls = [
                    tool_call_accumulator[i]
                    for i in sorted(tool_call_accumulator.keys())
                ]
            
            # Check if there are tool calls
            if accumulated_tool_calls:
                # Add assistant message with tool calls to messages
                self._messages.append({
                    "role": "assistant",
                    "content": accumulated_content or None,
                    "tool_calls": accumulated_tool_calls
                })
                
                # Yield tool calls chunk
                yield StreamingChunk(
                    type="tool_calls",
                    tool_calls=accumulated_tool_calls
                )
                
                # Add to chat history
                tool_call_entry = ChatEntry(
                    type="tool_call",
                    content="",
                    timestamp=datetime.now(),
                    tool_calls=accumulated_tool_calls
                )
                self._chat_history.append(tool_call_entry)
                
                # Execute each tool call
                for tool_call in accumulated_tool_calls:
                    tool_result = self._execute_tool(tool_call)
                    
                    # Add tool result to messages
                    self._messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.get("id"),
                        "content": json.dumps({
                            "success": tool_result.success,
                            "output": tool_result.output,
                            "error": tool_result.error
                        })
                    })
                    
                    # Yield tool result chunk
                    yield StreamingChunk(
                        type="tool_result",
                        tool_call=tool_call,
                        tool_result=tool_result
                    )
                    
                    # Add to chat history
                    result_entry = ChatEntry(
                        type="tool_result",
                        content=tool_result.output or tool_result.error or "",
                        timestamp=datetime.now(),
                        tool_call=tool_call,
                        tool_result=tool_result
                    )
                    self._chat_history.append(result_entry)
                
                # Increment tool rounds counter
                tool_rounds += 1
            else:
                # No tool calls, this is the final response
                # Add assistant message to messages
                self._messages.append({
                    "role": "assistant",
                    "content": accumulated_content
                })
                
                # Add to chat history
                assistant_entry = ChatEntry(
                    type="assistant",
                    content=accumulated_content,
                    timestamp=datetime.now()
                )
                self._chat_history.append(assistant_entry)
                
                # Yield done chunk
                yield StreamingChunk(type="done")
                
                # Exit the loop
                break
        
        # If we hit max tool rounds, yield a warning
        if tool_rounds >= self._max_tool_rounds:
            warning_content = f"Maximum tool execution rounds ({self._max_tool_rounds}) reached."
            yield StreamingChunk(type="content", content=warning_content)
            
            warning_entry = ChatEntry(
                type="assistant",
                content=warning_content,
                timestamp=datetime.now()
            )
            self._chat_history.append(warning_entry)
            
            yield StreamingChunk(type="done")
    
    def _execute_tool(self, tool_call: Dict[str, Any]) -> ToolResult:
        """Execute a tool call and return the result.
        
        Args:
            tool_call: The tool call dictionary from the AI response
        
        Returns:
            ToolResult with the execution result
        """
        function_data = tool_call.get("function", {})
        function_name = function_data.get("name")
        
        # Parse arguments
        try:
            arguments_str = function_data.get("arguments", "{}")
            arguments = json.loads(arguments_str)
        except json.JSONDecodeError as e:
            return ToolResult(
                success=False,
                output=None,
                error=f"Failed to parse tool arguments: {str(e)}"
            )
        
        # Dispatch to appropriate tool
        if function_name == "bash":
            command = arguments.get("command", "")
            if not command:
                return ToolResult(
                    success=False,
                    output=None,
                    error="No command provided"
                )
            return self._bash_tool.execute(command)
        else:
            return ToolResult(
                success=False,
                output=None,
                error=f"Unknown tool: {function_name}"
            )
    
    def get_chat_history(self) -> List[ChatEntry]:
        """Get the full chat history.
        
        Returns:
            List of all ChatEntry objects in chronological order
        """
        return self._chat_history.copy()
    
    def get_current_directory(self) -> str:
        """Get the current working directory.
        
        Returns:
            The current working directory path
        """
        return self._bash_tool.get_current_directory()
    
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
