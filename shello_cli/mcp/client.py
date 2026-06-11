import asyncio
import inspect
from collections.abc import Callable, Iterator
from typing import Any

from fastmcp import Client as AsyncMCPClient

from shello_cli.mcp.async_executor import AsyncExecutor


class MCPClient(AsyncMCPClient):
    """MCP client with sync helpers and lifecycle management.

    Extends fastmcp.Client to support running async methods from sync code.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._executor = AsyncExecutor()
        self._closed = False
        self._tools = []

    @property
    def tools(self) -> list:
        """The MCP tools using this client connection."""
        return list(self._tools)

    async def connect_async(self) -> None:
        """Establish connection to the MCP server."""
        try:
            await self.__aenter__()
        except RuntimeError as exc:
            raise RuntimeError("MCP Connection Failure") from exc

    def call_async_from_sync(
        self,
        awaitable_or_fn: Callable[..., Any] | Any,
        *args,
        timeout: float,
        **kwargs,
    ) -> Any:
        """Run a coroutine or async function on this client's loop from sync code."""
        return self._executor.run_async(
            awaitable_or_fn, *args, timeout=timeout, **kwargs
        )

    def sync_close(self) -> None:
        """Synchronously close the MCP client and cleanup resources."""
        if self._closed:
            return

        # Try async close if parent provides it
        if hasattr(self, "close") and inspect.iscoroutinefunction(self.close):
            try:
                self._executor.run_async(self.close, timeout=10.0)
            except Exception:
                pass

        # Cleanup the executor
        self._executor.close()
        self._closed = True

    def __del__(self):
        try:
            self.sync_close()
        except Exception:
            pass

    # Sync context manager support
    def __enter__(self) -> "MCPClient":
        return self

    def __exit__(self, *args: object) -> None:
        self.sync_close()
