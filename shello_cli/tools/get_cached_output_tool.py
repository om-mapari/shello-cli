"""Tool for retrieving specific lines from cached command output."""

from typing import Optional
from shello_cli.types import ToolResult
from shello_cli.tools.output.cache import OutputCache
from shello_cli.constants import DEFAULT_CHAR_LIMITS


class GetCachedOutputTool:
    """
    Tool for AI to retrieve specific line ranges from cached command output.
    
    This tool allows the AI agent to access full command output even when
    the bash_tool truncated it. The cache persists for the entire conversation.
    
    Parameters:
        cache_id: str - Cache ID from tool result (e.g., "cmd_001")
        lines: Optional[str] - Line specification:
            "+N"    - First N lines
            "-N"    - Last N lines
            "+N,-M" - First N + last M lines
            "N-M"   - Lines N through M (1-indexed)
            None    - Full output (with safety limit)
    """
    
    def __init__(self, cache: OutputCache):
        """Initialize the tool with a shared cache instance.
        
        Args:
            cache: Shared OutputCache instance (same one used by BashTool)
        """
        self._cache = cache
        self._safety_limit = DEFAULT_CHAR_LIMITS["safety"]
    
    def execute(self, cache_id: str, lines: Optional[str] = None) -> ToolResult:
        """Retrieve cached output with optional line selection.
        
        Args:
            cache_id: Cache ID from truncation summary
            lines: Optional line specification (+N, -N, +N,-M, N-M)
            
        Returns:
            ToolResult with retrieved output or error message
        """
        # Validate cache_id format
        if not cache_id or not isinstance(cache_id, str):
            return ToolResult(
                success=False,
                output="",
                error=f"Invalid cache_id: must be a non-empty string (e.g., 'cmd_001')"
            )
        
        # Try to retrieve from cache
        if lines is None:
            # Get full output
            output = self._cache.get(cache_id)
        else:
            # Get specific lines
            output = self._cache.get_lines(cache_id, lines)
        
        # Handle cache miss
        if output is None:
            return ToolResult(
                success=False,
                output="",
                error=(
                    f"Cache miss for '{cache_id}'. "
                    f"Possible reasons:\n"
                    f"  - Invalid cache ID (check the cache_id from tool result)\n"
                    f"  - Cache evicted due to size limit (100MB max)\n\n"
                    f"Solution: Re-run the original command to regenerate output."
                )
            )
        
        # Apply safety limit if getting full output
        if lines is None and len(output) > self._safety_limit:
            # Truncate to safety limit
            truncated = output[:self._safety_limit]
            # Find last complete line
            last_newline = truncated.rfind('\n')
            if last_newline > 0:
                truncated = truncated[:last_newline]
            
            warning = (
                f"\n\n[Output truncated to safety limit: {self._safety_limit:,} chars]\n"
                f"Use lines parameter to retrieve specific sections:\n"
                f"  - lines='+100' for first 100 lines\n"
                f"  - lines='-100' for last 100 lines\n"
                f"  - lines='+50,-50' for first 50 + last 50 lines"
            )
            
            return ToolResult(
                success=True,
                output=truncated + warning,
                error=None
            )
        
        # Return retrieved output
        return ToolResult(
            success=True,
            output=output,
            error=None
        )
    
    def get_cache_stats(self) -> dict:
        """Get cache statistics for debugging.
        
        Returns:
            Dictionary with cache statistics
        """
        return self._cache.get_stats()
