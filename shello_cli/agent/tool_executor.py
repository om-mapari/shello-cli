"""
Tool execution logic for the Shello Agent.

This module handles the execution of tools (bash, json_analyzer, etc.).
"""

import json
from typing import Dict, Any, Generator

from shello_cli.tools.bash_tool import BashTool
from shello_cli.tools.json_analyzer_tool import JsonAnalyzerTool
from shello_cli.tools.get_cached_output_tool import GetCachedOutputTool
from shello_cli.tools.output.cache import OutputCache
from shello_cli.types import ToolResult


class ToolExecutor:
    """Handles execution of tools requested by the AI."""
    
    def __init__(self):
        """Initialize the tool executor with available tools."""
        # Create shared cache instance
        self._output_cache = OutputCache()
        
        # Initialize tools with shared cache
        self._bash_tool = BashTool(output_cache=self._output_cache)
        self._json_analyzer_tool = JsonAnalyzerTool()
        self._get_cached_output_tool = GetCachedOutputTool(self._output_cache)
    
    def execute_tool(self, tool_call: Dict[str, Any]) -> ToolResult:
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
            is_safe = arguments.get("is_safe")
            if not command:
                return ToolResult(
                    success=False,
                    output=None,
                    error="No command provided"
                )
            return self._bash_tool.execute(command, is_safe=is_safe)
        elif function_name == "analyze_json":
            command = arguments.get("command", "")
            if not command:
                return ToolResult(
                    success=False,
                    output=None,
                    error="No command provided"
                )
            return self._json_analyzer_tool.analyze(command)
        elif function_name == "get_cached_output":
            cache_id = arguments.get("cache_id", "")
            lines = arguments.get("lines")
            if not cache_id:
                return ToolResult(
                    success=False,
                    output=None,
                    error="No cache_id provided"
                )
            return self._get_cached_output_tool.execute(cache_id, lines)
        else:
            return ToolResult(
                success=False,
                output=None,
                error=f"Unknown tool: {function_name}"
            )
    
    def execute_tool_stream(self, tool_call: Dict[str, Any]) -> Generator[str, None, ToolResult]:
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
            is_safe = arguments.get("is_safe")
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
            stream = self._bash_tool.execute_stream(command, is_safe=is_safe)
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
        elif function_name == "get_cached_output":
            cache_id = arguments.get("cache_id", "")
            lines = arguments.get("lines")
            if not cache_id:
                # Must be a generator - yield nothing and return error
                if False:
                    yield  # Make this a generator
                return ToolResult(
                    success=False,
                    output=None,
                    error="No cache_id provided"
                )
            # get_cached_output doesn't stream, but we yield the output for consistency
            result = self._get_cached_output_tool.execute(cache_id, lines)
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
    
    def get_current_directory(self) -> str:
        """Get the current working directory from bash tool.
        
        Returns:
            The current working directory path
        """
        return self._bash_tool.get_current_directory()
    
    def clear_cache(self) -> None:
        """Clear the output cache.
        
        This should be called when starting a new conversation or ending the session.
        """
        self._output_cache.clear()
