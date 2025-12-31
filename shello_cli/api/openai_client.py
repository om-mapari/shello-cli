"""
OpenAI-compatible API client for Shello CLI.

This module provides a client for interacting with OpenAI-compatible APIs,
supporting chat completions with tool calling and streaming responses.
"""

from typing import List, Optional, Dict, Any, Generator
from openai import OpenAI
from shello_cli.types import ShelloTool


class ShelloClient:
    """OpenAI-compatible API client for chat completions with tool support.
    
    This client wraps the OpenAI Python library to provide a consistent interface
    for chat completions with function calling capabilities.
    
    Attributes:
        _client: The underlying OpenAI client instance
        _model: The current model being used for completions
    """
    
    def __init__(self, api_key: str, model: str = "gpt-4o", base_url: Optional[str] = None):
        """Initialize the Shello client with API credentials.
        
        Args:
            api_key: OpenAI API key for authentication
            model: Model name to use for completions (default: "gpt-4o")
            base_url: Optional custom base URL for OpenAI-compatible endpoints
        
        Raises:
            ValueError: If api_key is None or empty
        """
        if not api_key:
            raise ValueError("API key cannot be None or empty")
        
        # Initialize OpenAI client with optional base_url
        if base_url:
            self._client = OpenAI(api_key=api_key, base_url=base_url)
        else:
            self._client = OpenAI(api_key=api_key)
        
        self._model = model
    
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
