"""
Tool execution for the Shello Agent.

All dispatch goes through the registry — no hardcoded if/elif chains.
Adding a new tool only requires registering it here; nothing else changes.
"""

import json
from typing import Dict, Any, Generator

from shello_cli.types import ToolResult
from shello_cli.tools.output.cache import OutputCache
from shello_cli.tools import registry

# Module-level imports kept here so tests can patch them at this location,
# e.g. patch('shello_cli.agent.tool_executor.BashTool')
from shello_cli.tools.bash_tool import BashTool
from shello_cli.tools.json_analyzer_tool import JsonAnalyzerTool
from shello_cli.tools.get_cached_output_tool import GetCachedOutputTool


class ToolExecutor:
    """Handles execution of tools requested by the AI."""

    def __init__(self):
        self._output_cache = OutputCache()
        self._register_tools()

    def _register_tools(self) -> None:
        """Instantiate tools with the shared cache and (re-)register them.

        Clears any previously registered tools first so the agent always
        uses the single shared OutputCache instance for both execution and
        cache retrieval.

        Module-level imports (BashTool, JsonAnalyzerTool, GetCachedOutputTool)
        are used here so tests can patch them at the tool_executor module level.
        """
        # Clear the registry so we own the shared cache (tools.py may have
        # registered throw-away instances for schema-only access).
        registry._REGISTRY.clear()

        bash = BashTool(output_cache=self._output_cache)
        registry.register(bash, name="run_shell_command")
        registry.register(JsonAnalyzerTool(bash_tool=bash), name="analyze_json")
        registry.register(GetCachedOutputTool(cache=self._output_cache), name="get_cached_output")

        # Store bash reference for helpers that need it directly
        self._bash_tool = bash

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    def execute_tool(self, tool_call: Dict[str, Any]) -> ToolResult:
        """Execute a tool call and return the result."""
        name, kwargs, err = self._parse(tool_call)
        if err:
            return err
        return registry.dispatch(name, **kwargs)

    def execute_tool_stream(self, tool_call: Dict[str, Any]) -> Generator[str, None, ToolResult]:
        """Execute a tool call with streaming output."""
        name, kwargs, err = self._parse(tool_call)
        if err:
            return err
            yield  # make this a generator
        return (yield from registry.dispatch_stream(name, **kwargs))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse(tool_call: Dict[str, Any]):
        """Extract name + kwargs from a raw tool_call dict.

        Returns (name, kwargs, None) on success or (None, None, ToolResult) on error.
        """
        fn = tool_call.get("function", {})
        name = fn.get("name")
        try:
            kwargs = json.loads(fn.get("arguments", "{}"))
        except json.JSONDecodeError as e:
            return None, None, ToolResult(
                success=False, output=None,
                error=f"Failed to parse tool arguments: {e}"
            )
        return name, kwargs, None

    def get_current_directory(self) -> str:
        return self._bash_tool.get_current_directory()

    def clear_cache(self) -> None:
        """Clear the output cache (call on /new or session end)."""
        self._output_cache.clear()
