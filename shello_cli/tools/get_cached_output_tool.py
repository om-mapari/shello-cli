"""Tool for retrieving specific lines from cached command output."""

from typing import Optional

from shello_cli.types import ToolResult, ShelloTool
from shello_cli.tools.base import ShelloToolBase
from shello_cli.tools.output.cache import OutputCache
from shello_cli.defaults import DEFAULT_CHAR_LIMITS


class GetCachedOutputTool(ShelloToolBase):
    """Retrieve specific line ranges from cached command output."""

    tool_name = "get_cached_output"

    _SCHEMA = ShelloTool(
        type="function",
        function={
            "name": "get_cached_output",
            "description": (
                "Retrieve cached output from previous command.\n\n"
                "USE WHEN: Output was truncated, user asks about earlier command,"
                " need specific lines.\n\n"
                "LINE SELECTION:\n"
                "  '-100'    -> Last 100 lines (best for logs)\n"
                "  '+50'     -> First 50 lines\n"
                "  '+20,-80' -> First 20 + last 80\n"
                "  '10-50'   -> Lines 10-50\n"
                "  (omit)    -> Full output (50K limit)\n\n"
                "EXAMPLE: get_cached_output(cache_id='cmd_001', lines='-100')"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "cache_id": {
                        "type": "string",
                        "description": "Cache ID from truncation summary (e.g., 'cmd_001')"
                    },
                    "lines": {
                        "type": "string",
                        "description": (
                            "Line selection: '+N' first, '-N' last,"
                            " '+N,-M' both, 'N-M' range. Omit for full."
                        )
                    }
                },
                "required": ["cache_id"]
            }
        }
    )

    def __init__(self, cache: OutputCache):
        self._cache = cache
        self._safety_limit = DEFAULT_CHAR_LIMITS["safety"]

    @property
    def schema(self) -> ShelloTool:
        return self._SCHEMA

    def execute(self, cache_id: str, lines: Optional[str] = None, **_) -> ToolResult:
        if not cache_id or not isinstance(cache_id, str):
            return ToolResult(
                success=False, output="",
                error="Invalid cache_id: must be a non-empty string (e.g., 'cmd_001')"
            )

        output = self._cache.get_lines(cache_id, lines) if lines else self._cache.get(cache_id)

        if output is None:
            return ToolResult(
                success=False, output="",
                error=(
                    f"Cache miss for '{cache_id}'.\n"
                    "Possible reasons:\n"
                    "  - Invalid cache ID (check the cache_id from tool result)\n"
                    "  - Cache evicted due to size limit (100MB max)\n\n"
                    "Solution: Re-run the original command to regenerate output."
                )
            )

        if lines is None and len(output) > self._safety_limit:
            truncated = output[:self._safety_limit]
            last_nl = truncated.rfind('\n')
            if last_nl > 0:
                truncated = truncated[:last_nl]
            warning = (
                f"\n\n[Output truncated to safety limit: {self._safety_limit:,} chars]\n"
                "Use lines parameter to retrieve specific sections:\n"
                "  - lines='+100' for first 100 lines\n"
                "  - lines='-100' for last 100 lines\n"
                "  - lines='+50,-50' for first 50 + last 50 lines"
            )
            return ToolResult(success=True, output=truncated + warning, error=None)

        return ToolResult(success=True, output=output, error=None)

    def get_cache_stats(self) -> dict:
        """Get cache statistics for debugging."""
        return self._cache.get_stats()
