"""
Message processing logic for the Shello Agent.

This module handles the conversation loop and message processing.
"""

import json
from typing import List, Dict, Any, Generator
from datetime import datetime

from shello_cli.api.openai_client import ShelloClient
from shello_cli.tools.tools import get_all_tools
from shello_cli.agent.models import ChatEntry, StreamingChunk
from shello_cli.agent.tool_executor import ToolExecutor


class MessageProcessor:
    """Handles message processing and conversation flow."""
    
    def __init__(
        self,
        client: ShelloClient,
        tool_executor: ToolExecutor,
        max_tool_rounds: int = 100
    ):
        """Initialize the message processor.
        
        Args:
            client: The OpenAI client for API communication
            tool_executor: The tool executor for running tools
            max_tool_rounds: Maximum number of tool execution rounds
        """
        self._client = client
        self._tool_executor = tool_executor
        self._max_tool_rounds = max_tool_rounds
    
    def process_message(
        self,
        messages: List[Dict[str, Any]],
        chat_history: List[ChatEntry]
    ) -> List[ChatEntry]:
        """Process messages through the AI and execute tools.
        
        Args:
            messages: The message list to send to the AI
            chat_history: The chat history to append to
        
        Returns:
            List of new ChatEntry objects from this processing round
        """
        entries: List[ChatEntry] = []
        
        # Tool execution loop
        tool_rounds = 0
        while tool_rounds < self._max_tool_rounds:
            # Get response from AI
            try:
                response = self._client.chat(
                    messages=messages,
                    tools=get_all_tools()
                )
            except Exception as e:
                error_entry = ChatEntry(
                    type="assistant",
                    content=f"Error communicating with AI: {str(e)}",
                    timestamp=datetime.now()
                )
                entries.append(error_entry)
                chat_history.append(error_entry)
                return entries
            
            # Extract the assistant's message
            choice = response.get("choices", [{}])[0]
            message_data = choice.get("message", {})
            
            # Check if there are tool calls
            tool_calls = message_data.get("tool_calls")
            
            if tool_calls:
                # Add assistant message with tool calls to messages
                messages.append({
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
                chat_history.append(tool_call_entry)
                
                # Execute each tool call
                for tool_call in tool_calls:
                    tool_result = self._tool_executor.execute_tool(tool_call)
                    
                    # Add tool result to messages
                    messages.append({
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
                    chat_history.append(result_entry)
                
                # Increment tool rounds counter
                tool_rounds += 1
            else:
                # No tool calls, this is the final response
                content = message_data.get("content", "")
                
                # Add assistant message to messages
                messages.append({
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
                chat_history.append(assistant_entry)
                
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
            chat_history.append(warning_entry)
        
        return entries
    
    def process_message_stream(
        self,
        messages: List[Dict[str, Any]],
        chat_history: List[ChatEntry]
    ) -> Generator[StreamingChunk, None, None]:
        """Process messages with streaming response.
        
        Args:
            messages: The message list to send to the AI
            chat_history: The chat history to append to
        
        Yields:
            StreamingChunk objects representing the conversation flow
        """
        # Tool execution loop
        tool_rounds = 0
        while tool_rounds < self._max_tool_rounds:
            # Get streaming response from AI
            try:
                stream = self._client.chat_stream(
                    messages=messages,
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
                messages.append({
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
                chat_history.append(tool_call_entry)
                
                # Execute each tool call
                for tool_call in accumulated_tool_calls:
                    # Yield tool call info first
                    yield StreamingChunk(
                        type="tool_call",
                        tool_call=tool_call
                    )
                    
                    # Execute tool with streaming
                    tool_stream = self._tool_executor.execute_tool_stream(tool_call)
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
                        from shello_cli.types import ToolResult
                        tool_result = ToolResult(
                            success=False,
                            output=None,
                            error="Tool execution did not return a result"
                        )
                    
                    # Add tool result to messages
                    messages.append({
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
                    chat_history.append(result_entry)
                
                # Increment tool rounds counter
                tool_rounds += 1
            else:
                # No tool calls, this is the final response
                # Add assistant message to messages
                messages.append({
                    "role": "assistant",
                    "content": accumulated_content
                })
                
                # Add to chat history
                assistant_entry = ChatEntry(
                    type="assistant",
                    content=accumulated_content,
                    timestamp=datetime.now()
                )
                chat_history.append(assistant_entry)
                
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
            chat_history.append(warning_entry)
            
            yield StreamingChunk(type="done")
