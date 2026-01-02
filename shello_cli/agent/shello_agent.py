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
from pathlib import Path

from shello_cli.api.openai_client import ShelloClient
from shello_cli.tools.bash_tool import BashTool
from shello_cli.tools.json_analyzer_tool import JsonAnalyzerTool
from shello_cli.tools.tools import get_all_tools, get_tool_descriptions
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
        
        # Initialize tools
        self._bash_tool = BashTool()
        self._json_analyzer_tool = JsonAnalyzerTool()
        
        # Initialize conversation tracking
        self._chat_history: List[ChatEntry] = []
        self._messages: List[Dict[str, Any]] = []
        
        # Store configuration
        self._max_tool_rounds = max_tool_rounds
        
        # Load custom instructions if available
        custom_instructions = self._load_custom_instructions()
        custom_instructions_section = ""
        if custom_instructions:
            custom_instructions_section = f"\n\nCUSTOM INSTRUCTIONS:\n{custom_instructions}\n\nThe above custom instructions should be followed alongside the standard instructions below."
        
        # Get system information
        os_name = platform.system()
        
        # Detect actual shell being used
        if os_name == 'Windows':
            # Check for bash first (Git Bash, WSL, etc.)
            if os.environ.get('BASH') or os.environ.get('BASH_VERSION'):
                shell = os.environ.get('BASH', 'bash')
                shell_name = 'bash'
            # Check SHELL environment variable for bash (Git Bash on Windows)
            # Also check SHLVL which is set by bash but not cmd/PowerShell
            elif (os.environ.get('SHELL') and 'bash' in os.environ.get('SHELL', '').lower()) or \
                 os.environ.get('SHLVL'):
                shell = os.environ.get('SHELL', 'bash')
                shell_name = 'bash'
            # Check if running in PowerShell (but not if bash is present)
            # PSExecutionPolicyPreference is only set when actually running in PowerShell
            elif os.environ.get('PSExecutionPolicyPreference') or \
                 (os.environ.get('PSModulePath') and not os.environ.get('PROMPT', '').startswith('$P$G')):
                shell_name = 'powershell'
                shell = os.environ.get('COMSPEC', 'cmd.exe')
            else:
                shell = os.environ.get('COMSPEC', 'cmd.exe')
                shell_name = 'cmd'
        else:
            # On Unix-like systems, use SHELL environment variable
            shell = os.environ.get('SHELL', '/bin/bash')
            shell_name = os.path.basename(shell)
        
        cwd = self._bash_tool.get_current_directory()
        current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Get tool descriptions dynamically
        tool_descriptions = get_tool_descriptions()
        
        # Format the system prompt with current information
        system_prompt = INSTRUCTION_TEMPLATE.format(
            custom_instructions=custom_instructions_section,
            tool_descriptions=tool_descriptions,
            os_name=os_name,
            shell=shell_name,
            shell_executable=shell,
            cwd=cwd,
            current_datetime=current_datetime
        )
        
        # Add system message
        self._messages.append({
            "role": "system",
            "content": system_prompt
        })
    
    def _load_custom_instructions(self) -> Optional[str]:
        """Load custom instructions from .shello/SHELLO.md if available.
        
        Checks in order:
        1. Current working directory: .shello/SHELLO.md
        2. User home directory: ~/.shello/SHELLO.md
        
        Returns:
            Optional[str]: Custom instructions content or None if not found
        """
        try:
            # Check current working directory
            cwd_path = Path.cwd() / ".shello" / "SHELLO.md"
            if cwd_path.exists():
                return cwd_path.read_text(encoding='utf-8').strip()
            
            # Check user home directory
            home_path = Path.home() / ".shello" / "SHELLO.md"
            if home_path.exists():
                return home_path.read_text(encoding='utf-8').strip()
            
            return None
        except Exception as e:
            # Silently fail if we can't load custom instructions
            return None
    
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
                if "tool_calls" in delta and delta["tool_calls"] is not None:
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
                    # Yield tool call info first
                    yield StreamingChunk(
                        type="tool_call",
                        tool_call=tool_call
                    )
                    
                    # Execute tool with streaming
                    tool_stream = self._execute_tool_stream(tool_call)
                    tool_result = None
                    
                    # Stream tool output - manually iterate to catch StopIteration
                    while True:
                        try:
                            output_chunk = next(tool_stream)
                            # All chunks from the generator are strings (output)
                            yield StreamingChunk(
                                type="tool_output",
                                content=output_chunk,
                                tool_call=tool_call
                            )
                        except StopIteration as e:
                            # The return value is in the exception
                            tool_result = e.value
                            break
                    
                    # If we didn't get a result from StopIteration, something went wrong
                    if tool_result is None:
                        tool_result = ToolResult(
                            success=False,
                            output=None,
                            error="Tool execution did not return a result"
                        )
                    
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
        elif function_name == "analyze_json":
            command = arguments.get("command", "")
            if not command:
                return ToolResult(
                    success=False,
                    output=None,
                    error="No command provided"
                )
            return self._json_analyzer_tool.analyze(command)
        else:
            return ToolResult(
                success=False,
                output=None,
                error=f"Unknown tool: {function_name}"
            )
    
    def _execute_tool_stream(self, tool_call: Dict[str, Any]) -> Generator[str, None, ToolResult]:
        """Execute a tool call with streaming output.
        
        Args:
            tool_call: The tool call dictionary from the AI response
        
        Yields:
            Output chunks as they arrive from the tool
        
        Returns:
            ToolResult with the final execution result
        """
        function_data = tool_call.get("function", {})
        function_name = function_data.get("name")
        
        # Parse arguments
        try:
            arguments_str = function_data.get("arguments", "{}")
            arguments = json.loads(arguments_str)
        except json.JSONDecodeError as e:
            # Must be a generator - yield nothing and return error
            if False:
                yield  # Make this a generator
            return ToolResult(
                success=False,
                output=None,
                error=f"Failed to parse tool arguments: {str(e)}"
            )
        
        # Dispatch to appropriate tool
        if function_name == "bash":
            command = arguments.get("command", "")
            if not command:
                # Must be a generator - yield nothing and return error
                if False:
                    yield  # Make this a generator
                return ToolResult(
                    success=False,
                    output=None,
                    error="No command provided"
                )
            # Use streaming bash execution - yield from the generator
            stream = self._bash_tool.execute_stream(command)
            result = None
            try:
                while True:
                    chunk = next(stream)
                    yield chunk
            except StopIteration as e:
                result = e.value
            return result
        elif function_name == "analyze_json":
            command = arguments.get("command", "")
            if not command:
                # Must be a generator - yield nothing and return error
                if False:
                    yield  # Make this a generator
                return ToolResult(
                    success=False,
                    output=None,
                    error="No command provided"
                )
            # JSON analyzer doesn't stream, but we yield the output for consistency
            result = self._json_analyzer_tool.analyze(command)
            if result.output:
                yield result.output
            return result
        else:
            # Must be a generator - yield nothing and return error
            if False:
                yield  # Make this a generator
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
