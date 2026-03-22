"""
Base class for all Shello tools.

Provides a common interface that links the tool's JSON schema to its
executor, eliminating the string-name coupling between tools.py and
tool_executor.py.
"""

from abc import ABC, abstractmethod
from typing import Generator

from shello_cli.types import ToolResult, ShelloTool


class ShelloToolBase(ABC):
    """Abstract base for all Shello tools.

    Subclasses must define:
      - tool_name: class-level string constant — the single source of truth
                   for the tool's name used in registry dispatch and schema.
      - schema: the ShelloTool (JSON schema for the LLM)
      - execute(**kwargs): the actual implementation

    tool_name is a plain class attribute so it remains a real string even
    when the class is mocked in tests (mock.schema.function["name"] would
    return a MagicMock, but mock.tool_name is still patchable as a string).
    """

    tool_name: str  # must be set on each concrete subclass

    @property
    @abstractmethod
    def schema(self) -> ShelloTool:
        """Return the OpenAI function-calling schema for this tool."""
        ...

    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        """Execute the tool with the given arguments."""
        ...

    def execute_stream(self, **kwargs) -> Generator[str, None, ToolResult]:
        """Execute with streaming output.

        Default implementation runs execute() and yields the output once.
        Override in tools that support real streaming (e.g. BashTool).
        """
        result = self.execute(**kwargs)
        if result.output:
            yield result.output
        return result
