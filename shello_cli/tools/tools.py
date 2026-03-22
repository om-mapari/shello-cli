"""
Tool schema access for Shello CLI.

Eagerly registers all tools so SHELLO_TOOLS and get_all_tools() work
at import time (required by tests and the system prompt builder).

The registry is the single source of truth - tools.py is just the
public surface that the rest of the codebase imports from.
"""

from typing import List

from shello_cli.types import ShelloTool
from shello_cli.tools import registry
from shello_cli.tools.output.cache import OutputCache


def _ensure_registered() -> None:
    """Register all tools if the registry is empty.

    Uses a throw-away cache instance so schemas are available without
    a live ToolExecutor. The real ToolExecutor creates its own shared
    cache and re-registers with that instance.
    """
    if registry._REGISTRY:
        return

    from shello_cli.tools.bash_tool import BashTool
    from shello_cli.tools.json_analyzer_tool import JsonAnalyzerTool
    from shello_cli.tools.get_cached_output_tool import GetCachedOutputTool

    cache = OutputCache()
    bash = BashTool(output_cache=cache)
    registry.register(bash, name=BashTool.tool_name)
    registry.register(JsonAnalyzerTool(bash_tool=bash), name=JsonAnalyzerTool.tool_name)
    registry.register(GetCachedOutputTool(cache=cache), name=GetCachedOutputTool.tool_name)


_ensure_registered()

# Backward-compat export used by tests
SHELLO_TOOLS: List[ShelloTool] = registry.get_all_schemas()


def get_all_tools() -> List[ShelloTool]:
    """Return all registered tool schemas for the LLM tools parameter."""
    return registry.get_all_schemas()


def get_tool_descriptions() -> str:
    """Generate one-line tool descriptions for the system prompt."""
    lines = []
    for tool in registry.get_all_schemas():
        name = tool.function["name"]
        first_line = tool.function["description"].split("\n")[0]
        lines.append(f"- {name}: {first_line}")
    return "\n".join(lines)
