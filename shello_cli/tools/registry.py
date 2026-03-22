"""
Tool registry for Shello CLI.

Tools register themselves here on import. The registry is the single
source of truth for both schema discovery (get_all_schemas) and
dispatch (dispatch / dispatch_stream).

Adding a new tool:
  1. Create a class that extends ShelloToolBase
  2. Call register(MyTool()) at the bottom of the module
  3. Import the module anywhere before the agent starts
     (tool_executor.py does this in _register_tools)
"""

from typing import Generator

from shello_cli.types import ToolResult, ShelloTool
from shello_cli.tools.base import ShelloToolBase

_REGISTRY: dict[str, ShelloToolBase] = {}


def register(tool: ShelloToolBase, name: str | None = None) -> None:
    """Register a tool instance.

    Args:
        tool: The tool instance to register.
        name: Override the registration key. When omitted, uses tool.tool_name.
              Pass explicitly when the tool class may be mocked in tests.
    """
    key = name if name is not None else tool.tool_name
    if key in _REGISTRY:
        raise ValueError(f"Tool '{key}' is already registered")
    _REGISTRY[key] = tool


def get_all_schemas() -> list[ShelloTool]:
    """Return all registered tool schemas (for the LLM tools parameter)."""
    return [t.schema for t in _REGISTRY.values()]


def dispatch(name: str, **kwargs) -> ToolResult:
    """Dispatch a tool call by name."""
    tool = _REGISTRY.get(name)
    if tool is None:
        return ToolResult(
            success=False,
            output=None,
            error=f"Unknown tool: '{name}'. Available: {list(_REGISTRY)}"
        )
    return tool.execute(**kwargs)


def dispatch_stream(name: str, **kwargs) -> Generator[str, None, ToolResult]:
    """Dispatch a streaming tool call by name."""
    tool = _REGISTRY.get(name)
    if tool is None:
        return ToolResult(
            success=False,
            output=None,
            error=f"Unknown tool: '{name}'. Available: {list(_REGISTRY)}"
        )
        yield  # make this a generator
    return (yield from tool.execute_stream(**kwargs))
