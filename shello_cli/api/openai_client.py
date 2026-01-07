"""
OpenAI-compatible API client for Shello CLI.

This module provides a client for interacting with OpenAI-compatible APIs,
supporting chat completions with tool calling and streaming responses.
"""

import json
from typing import List, Optional, Dict, Any, Generator
from openai import OpenAI
import httpx
from shello_cli.types import ShelloTool


class ShelloClient:
    """OpenAI-compatible API client for chat completions with tool support.
    
    This client wraps the OpenAI Python library to provide a consistent interface
    for chat completions with function calling capabilities.
    
    Attributes:
        _client: The underlying OpenAI client instance
        _model: The current model being used for completions
    """
    
    def __init__(self, api_key: str, model: str = "gpt-4o", base_url: Optional[str] = None, debug: bool = True):
        """Initialize the Shello client with API credentials.
        
        Args:
            api_key: OpenAI API key for authentication
            model: Model name to use for completions (default: "gpt-4o")
            base_url: Optional custom base URL for OpenAI-compatible endpoints
            debug: Enable detailed HTTP request/response logging (default: False)
        
        Raises:
            ValueError: If api_key is None or empty
        """
        if not api_key:
            raise ValueError("API key cannot be None or empty")
        
        self._model = model
        self._debug = debug
        
        # Create HTTP client with logging hooks if debug is enabled
        if debug:
            http_client = httpx.Client(
                event_hooks={
                    'request': [self._log_request],
                    'response': [self._log_response]
                }
            )
            
            if base_url:
                self._client = OpenAI(api_key=api_key, base_url=base_url, http_client=http_client)
            else:
                self._client = OpenAI(api_key=api_key, http_client=http_client)
        else:
            # Initialize OpenAI client without logging
            if base_url:
                self._client = OpenAI(api_key=api_key, base_url=base_url)
            else:
                self._client = OpenAI(api_key=api_key)
    
    def _log_request(self, request: httpx.Request) -> None:
        """Log HTTP request details for debugging.
        
        Args:
            request: The HTTP request object
        """
        print("\n" + "="*80)
        print("🔵 OPENAI API REQUEST")
        print("="*80)
        
        try:
            body = json.loads(request.content.decode('utf-8'))
            
            # Extract key information
            model = body.get('model', 'unknown')
            messages = body.get('messages', [])
            tools = body.get('tools', [])
            stream = body.get('stream', False)
            
            print(f"Model: {model}")
            print(f"Stream: {stream}")
            print(f"\n📨 Messages ({len(messages)}):")
            
            # Show full message content
            for i, msg in enumerate(messages, 1):
                role = msg.get('role', 'unknown')
                content = msg.get('content', '')
                tool_calls = msg.get('tool_calls', [])
                tool_call_id = msg.get('tool_call_id', None)
                
                print(f"\n  [{i}] Role: {role.upper()}")
                print(f"  {'─' * 76}")
                
                # Show content FIRST (if present)
                has_content = isinstance(content, str) and content
                if has_content:
                    # For system messages, show only first line
                    if role.lower() == 'system':
                        first_line = content.split('\n')[0]
                        print(f"  {first_line}")
                        print(f"  ... (system prompt truncated)")
                    else:
                        # Show full content for user/assistant/tool messages
                        lines = content.split('\n')
                        for line in lines[:50]:  # Limit to first 50 lines per message
                            print(f"  {line}")
                        if len(lines) > 50:
                            print(f"  ... ({len(lines) - 50} more lines)")
                
                # Show tool calls AFTER content (if present)
                if tool_calls:
                    # Add visual separator if there was content before
                    if has_content:
                        print(f"\n  {'─' * 76}")
                    
                    print(f"  🔧 Tool Calls: {len(tool_calls)}")
                    for tc in tool_calls:
                        func = tc.get('function', {})
                        func_name = func.get('name', 'unknown')
                        func_args = func.get('arguments', '{}')
                        tc_id = tc.get('id', 'unknown')
                        
                        print(f"\n    • Function: {func_name}")
                        print(f"      Call ID: {tc_id}")
                        print(f"      Arguments:")
                        
                        # Pretty print the arguments
                        try:
                            args_obj = json.loads(func_args)
                            args_str = json.dumps(args_obj, indent=8)
                            # Indent each line
                            for line in args_str.split('\n'):
                                print(f"      {line}")
                        except:
                            print(f"        {func_args}")
                
                # Show tool call ID if this is a tool result message
                if tool_call_id:
                    print(f"  🔧 Tool Result for Call ID: {tool_call_id}")
                
                # Show status if neither content nor tool calls
                if not has_content and not tool_calls and not tool_call_id:
                    print(f"  <no content>")
                elif not isinstance(content, str) and content is not None:
                    print(f"  <complex content: {type(content).__name__}>")
            
            # Show tools summary
            if tools:
                print(f"\n🛠️  Tools ({len(tools)}):")
                for tool in tools:
                    func = tool.get('function', {})
                    name = func.get('name', 'unknown')
                    desc = func.get('description', 'No description')
                    print(f"  • {name}")
                    # Show first line of description
                    desc_line = desc.split('\n')[0][:70]
                    print(f"    {desc_line}")
            
        except Exception as e:
            print(f"Body: <unable to parse: {e}>")
        
        print("="*80 + "\n")
    
    def _log_response(self, response: httpx.Response) -> None:
        """Log HTTP response details for debugging.
        
        Args:
            response: The HTTP response object
        """
        print("\n" + "="*80)
        print("🟢 OPENAI API RESPONSE")
        print("="*80)
        print(f"Status: {response.status_code} ({response.reason_phrase})")
        
        # Only log body for non-streaming responses
        # Streaming responses will be consumed by the iterator
        if response.headers.get("content-type", "").startswith("text/event-stream"):
            print(f"Type: Streaming response")
            print(f"Note: Chunks will be processed by the stream iterator")
        else:
            try:
                # Check if response has been read
                if not hasattr(response, "_content"):
                    # Response hasn't been read yet, read it now
                    response.read()
                
                body = json.loads(response.text)
                
                # Extract key information from response
                choices = body.get('choices', [])
                usage = body.get('usage', {})
                model = body.get('model', 'unknown')
                
                print(f"Model: {model}")
                
                if usage:
                    print(f"Usage:")
                    print(f"  Prompt tokens: {usage.get('prompt_tokens', 0)}")
                    print(f"  Completion tokens: {usage.get('completion_tokens', 0)}")
                    print(f"  Total tokens: {usage.get('total_tokens', 0)}")
                
                if choices:
                    print(f"\nChoices: {len(choices)}")
                    for i, choice in enumerate(choices, 1):
                        message = choice.get('message', {})
                        content = message.get('content', '')
                        tool_calls = message.get('tool_calls', [])
                        finish_reason = choice.get('finish_reason', 'unknown')
                        
                        print(f"  [{i}] Finish reason: {finish_reason}")
                        
                        # Check if both content and tool_calls are present
                        has_content = content and isinstance(content, str)
                        has_tool_calls = tool_calls and len(tool_calls) > 0
                        
                        if has_content and has_tool_calls:
                            print(f"      ✨ BOTH content AND tool_calls present!")
                        
                        if has_content:
                            preview = content[:100].replace('\n', ' ')
                            if len(content) > 100:
                                preview += "..."
                            print(f"      Content: {preview}")
                        
                        if has_tool_calls:
                            print(f"      Tool calls: {len(tool_calls)}")
                            for tc in tool_calls:
                                func = tc.get('function', {})
                                print(f"        - {func.get('name', 'unknown')}")
                
            except Exception as e:
                print(f"Body: <unable to parse: {e}>")
                # Don't try to access response.text if it failed above
        
        print("="*80 + "\n")
    
    def set_model(self, model: str) -> None:
        """Change the current model used for completions.
        
        Args:
            model: The model name to use for future completions
        """
        self._model = model
    
    def get_current_model(self) -> str:
        """Get the current model name.
        
        Returns:
            The name of the model currently being used
        """
        return self._model
    
    def chat(self, messages: List[Dict[str, Any]], tools: Optional[List[ShelloTool]] = None) -> Dict[str, Any]:
        """Send a chat completion request and return the response.
        
        Args:
            messages: List of message dictionaries with role and content
            tools: Optional list of tools available for function calling
        
        Returns:
            Dictionary containing the API response with choices, usage, etc.
        
        Raises:
            Exception: If the API request fails
        """
        # Prepare the request parameters
        request_params: Dict[str, Any] = {
            "model": self._model,
            "messages": messages
        }
        
        # Add tools if provided
        if tools:
            # Convert ShelloTool objects to dictionaries
            tools_dicts = [
                {
                    "type": tool.type,
                    "function": tool.function
                }
                for tool in tools
            ]
            request_params["tools"] = tools_dicts
        
        try:
            # Make the API call
            response = self._client.chat.completions.create(**request_params)
            
            # Convert response to dictionary format
            return response.model_dump()
        except Exception as e:
            # Re-raise with descriptive error message
            raise Exception(f"OpenAI API error: {str(e)}") from e

    
    def chat_stream(self, messages: List[Dict[str, Any]], tools: Optional[List[ShelloTool]] = None) -> Generator[Dict[str, Any], None, None]:
        """Stream chat completion response chunks as they arrive.
        
        This method yields response chunks as they are received from the API,
        allowing for real-time display of the assistant's response.
        
        Args:
            messages: List of message dictionaries with role and content
            tools: Optional list of tools available for function calling
        
        Yields:
            Dictionary chunks containing delta updates from the streaming response
        
        Raises:
            Exception: If the API request fails
        """
        # Prepare the request parameters
        request_params: Dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "stream": True
        }
        
        # Add tools if provided
        if tools:
            # Convert ShelloTool objects to dictionaries
            tools_dicts = [
                {
                    "type": tool.type,
                    "function": tool.function
                }
                for tool in tools
            ]
            request_params["tools"] = tools_dicts
        
        try:
            # Make the streaming API call
            stream = self._client.chat.completions.create(**request_params)
            
            if stream is None:
                raise Exception("API returned None for streaming request")
            
            # Yield each chunk as it arrives
            for chunk in stream:
                if chunk is not None:
                    yield chunk.model_dump()
        except Exception as e:
            # Re-raise with descriptive error message
            raise Exception(f"OpenAI API streaming error: {str(e)}") from e
